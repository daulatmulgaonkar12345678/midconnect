"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import {
  BarChart3, TrendingUp, Package, Users, Calendar, Filter,
  IndianRupee, DollarSign, PieChart, Download, Upload, FileSpreadsheet,
  FileText, X, CheckCircle2, AlertCircle, Loader2, FileDown, Eye,
  Clock, ShoppingCart, ArrowLeftRight, ChevronLeft, ChevronRight, Search,
  BookOpen, Zap, FolderOpen, AlertTriangle
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type Tab = "sales" | "profit" | "product-profit" | "inventory-value" | "products" | "inventory" | "buyers" | "outstanding" | "purchase" | "stock-movement" | "buyer-ledger" | "product-perf" | "category" | "low-stock";

interface SalesPeriod { label: string; totalSales: number; totalGst: number; invoiceCount: number; avgInvoiceValue: number; }
interface ProfitPeriod { label: string; revenue: number; cost: number; profit: number; margin: number; invoiceCount: number; totalQuantity: number; }
interface ProductProfit { productName: string; totalQuantity: number; totalRevenue: number; totalCost: number; profit: number; margin: number; invoiceCount: number; }
interface InventoryValueItem { id: string; productName: string; productType: string; stock: number; purchase_price: number; selling_price: number; stockValue: number; potentialRevenue: number; }
interface ProductSale { productName: string; hsnCode?: string; totalQuantity: number; taxableValue?: number; gstPercent?: number; totalGst?: number; totalRevenue: number; invoiceCount: number; }
interface InventoryItem { id: string; productName: string; stock: number; lowStockAlert: number; isLowStock: boolean; sku?: string; }
interface TopBuyer { buyerId: string; buyerName: string; company: string; totalSpent: number; invoiceCount: number; lastInvoiceDate?: string; }

interface OutstandingItem {
  invoiceId: string; invoiceNumber: string; buyerId: string; buyerName: string; company: string;
  invoiceDate: string; dueDate: string; totalAmount: number; paidAmount: number;
  pendingAmount: number; daysOverdue: number; agingBucket: string; status: string;
}
interface PurchaseItem {
  poId: string; poNumber: string; supplierId: string; supplierName: string; supplierPhone: string;
  status: string; totalAmount: number; itemCount: number; createdAt: string; productNames: string;
}
interface StockMovementItem {
  listingId: string; productName: string; openingStock: number; inward: number;
  outward: number; adjustment: number; closingStock: number; logCount: number;
}
interface Pagination { page: number; limit: number; total: number; pages: number; }

interface BuyerLedgerItem {
  buyerId: string; buyerName: string; company: string; totalSales: number;
  totalPaid: number; pendingAmount: number; invoiceCount: number;
  lastInvoiceDate: string | null; lastPaymentDate: string | null;
}
interface BuyerTransaction {
  invoiceId: string; invoiceNumber: string; date: string; totalAmount: number;
  paidAmount: number; pendingAmount: number; status: string; products: string;
}
interface ProductPerfItem {
  productName: string; hsnCode?: string; quantitySold: number; revenue: number; profit: number;
  profitPercent: number; invoiceCount: number;
}
interface CategoryItem {
  categoryName: string; totalSales: number; revenue: number; profit: number;
  profitPercent: number; itemCount: number;
}
interface LowStockItem {
  listingId: string; productName: string; minStock: number; currentStock: number;
  timesHitLow: number; avgConsumption: number; totalSold: number;
  isLowStock: boolean; isOutOfStock: boolean; daysOfStock: number;
}

const TAB_EXPORT_MAP: Record<Tab, string> = {
  sales: "sales", profit: "profit", "product-profit": "profit",
  "inventory-value": "inventory", products: "sales",
  inventory: "inventory", buyers: "buyers",
  outstanding: "outstanding", purchase: "purchase-orders",
  "stock-movement": "stock-movement",
  "buyer-ledger": "buyer-ledger", "product-perf": "product-performance",
  category: "category-report", "low-stock": "low-stock"
};

type ImportType = "products" | "inventory" | "suppliers" | "buyers";

export default function ReportsPage() {
  const { hasPermission, token } = usePermissions();
  const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
  const initialTab = (searchParams?.get("tab") as Tab) || "outstanding";
  const [tab, setTab] = useState<Tab>(initialTab);
  const [period, setPeriod] = useState("monthly");
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const [salesData, setSalesData] = useState<{ overall: Record<string, number>; periods: SalesPeriod[] }>({ overall: {}, periods: [] });
  const [profitData, setProfitData] = useState<{ overall: Record<string, number>; periods: ProfitPeriod[] }>({ overall: {}, periods: [] });
  const [productProfitData, setProductProfitData] = useState<ProductProfit[]>([]);
  const [inventoryValueData, setInventoryValueData] = useState<{ summary: Record<string, number>; items: InventoryValueItem[] }>({ summary: {}, items: [] });
  const [productData, setProductData] = useState<ProductSale[]>([]);
  const [inventoryData, setInventoryData] = useState<{ summary: Record<string, number>; items: InventoryItem[] }>({ summary: {}, items: [] });
  const [buyerData, setBuyerData] = useState<TopBuyer[]>([]);

  // New report states
  const [outstandingData, setOutstandingData] = useState<{ summary: Record<string, number>; aging: { buckets: Record<string, number>; counts: Record<string, number> }; items: OutstandingItem[]; pagination: Pagination }>({
    summary: {}, aging: { buckets: {}, counts: {} }, items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });
  const [purchaseData, setPurchaseData] = useState<{ summary: Record<string, number>; items: PurchaseItem[]; pagination: Pagination }>({
    summary: {}, items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });
  const [stockMovementData, setStockMovementData] = useState<{ summary: Record<string, number>; items: StockMovementItem[]; pagination: Pagination }>({
    summary: {}, items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });
  const [reportPage, setReportPage] = useState(1);
  const [buyerFilter, setBuyerFilter] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  // Filter option lists
  const [buyerOptions, setBuyerOptions] = useState<{ id: string; name: string }[]>([]);
  const [supplierOptions, setSupplierOptions] = useState<{ id: string; name: string }[]>([]);
  const [productOptions, setProductOptions] = useState<{ id: string; name: string }[]>([]);

  // Phase 2 report states
  const [buyerLedgerData, setBuyerLedgerData] = useState<{ summary: Record<string, number>; items: BuyerLedgerItem[]; pagination: Pagination }>({
    summary: {}, items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });
  const [selectedBuyer, setSelectedBuyer] = useState<string | null>(null);
  const [buyerTransactions, setBuyerTransactions] = useState<{ buyer: Record<string, string>; transactions: BuyerTransaction[]; pagination: Pagination } | null>(null);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [productPerfData, setProductPerfData] = useState<{ summary: Record<string, number>; topSelling: ProductPerfItem[]; slowMoving: ProductPerfItem[]; items: ProductPerfItem[]; pagination: Pagination }>({
    summary: {}, topSelling: [], slowMoving: [], items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });
  const [categoryData, setCategoryData] = useState<{ summary: Record<string, number>; items: CategoryItem[] }>({ summary: {}, items: [] });
  const [lowStockData, setLowStockData] = useState<{ summary: Record<string, number>; items: LowStockItem[]; pagination: Pagination }>({
    summary: {}, items: [], pagination: { page: 1, limit: 100, total: 0, pages: 1 }
  });

  const [startDate, setStartDate] = useState(() => { const d = new Date(); d.setFullYear(d.getFullYear() - 1); return d.toISOString().split("T")[0]; });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);

  // Import state
  const [showImport, setShowImport] = useState(false);
  const [importType, setImportType] = useState<ImportType>("products");
  const [importStep, setImportStep] = useState<"select" | "preview" | "result">("select");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importValidating, setImportValidating] = useState(false);
  const [importProcessing, setImportProcessing] = useState(false);
  const [importValidation, setImportValidation] = useState<any>(null);
  const [importResult, setImportResult] = useState<any>(null);

  const authHeaders = () => ({ Authorization: `Bearer ${token}` });

  const fetchReport = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    const h = { Authorization: `Bearer ${token}` };
    const dateParams = `startDate=${new Date(startDate).toISOString()}&endDate=${new Date(endDate).toISOString()}`;

    try {
      if (tab === "sales") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/sales-summary?${dateParams}&period=${period}`, { headers: h });
        setSalesData(await res.json());
      } else if (tab === "profit") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/profit-summary?${dateParams}&period=${period}`, { headers: h });
        setProfitData(await res.json());
      } else if (tab === "product-profit") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/product-profit?${dateParams}`, { headers: h });
        setProductProfitData((await res.json()).products || []);
      } else if (tab === "inventory-value") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/inventory-value`, { headers: h });
        setInventoryValueData(await res.json());
      } else if (tab === "products") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/product-sales?${dateParams}`, { headers: h });
        setProductData((await res.json()).products || []);
      } else if (tab === "inventory") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/inventory-status`, { headers: h });
        setInventoryData(await res.json());
      } else if (tab === "buyers") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/top-buyers?${dateParams}`, { headers: h });
        setBuyerData((await res.json()).buyers || []);
      } else if (tab === "outstanding") {
        const buyerParam = buyerFilter ? `&buyerId=${buyerFilter}` : "";
        const res = await fetch(`${API_URL}/api/business-tools/reports/outstanding?${dateParams}&page=${reportPage}&limit=100${buyerParam}`, { headers: h });
        setOutstandingData(await res.json());
      } else if (tab === "purchase") {
        const supplierParam = supplierFilter ? `&supplierId=${supplierFilter}` : "";
        const res = await fetch(`${API_URL}/api/business-tools/reports/purchase?${dateParams}&page=${reportPage}&limit=100${supplierParam}`, { headers: h });
        setPurchaseData(await res.json());
      } else if (tab === "stock-movement") {
        const productParam = productFilter ? `&listingId=${productFilter}` : "";
        const res = await fetch(`${API_URL}/api/business-tools/reports/stock-movement?${dateParams}&page=${reportPage}&limit=100${productParam}`, { headers: h });
        setStockMovementData(await res.json());
      } else if (tab === "buyer-ledger") {
        const buyerParam = buyerFilter ? `&buyerId=${buyerFilter}` : "";
        const res = await fetch(`${API_URL}/api/business-tools/reports/buyer-ledger?${dateParams}&page=${reportPage}&limit=100${buyerParam}`, { headers: h });
        setBuyerLedgerData(await res.json());
        setSelectedBuyer(null); setBuyerTransactions(null);
      } else if (tab === "product-perf") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/product-performance?${dateParams}&page=${reportPage}&limit=100`, { headers: h });
        setProductPerfData(await res.json());
      } else if (tab === "category") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/category-report?${dateParams}`, { headers: h });
        setCategoryData(await res.json());
      } else if (tab === "low-stock") {
        const res = await fetch(`${API_URL}/api/business-tools/reports/low-stock-analytics?${dateParams}&page=${reportPage}&limit=100`, { headers: h });
        setLowStockData(await res.json());
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [token, tab, period, startDate, endDate, reportPage, buyerFilter, supplierFilter, productFilter]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

  // Fetch filter options for new reports
  useEffect(() => {
    if (!token) return;
    const h = { Authorization: `Bearer ${token}` };
    // Fetch buyers for outstanding filter
    fetch(`${API_URL}/api/business-tools/buyers?limit=200`, { headers: h })
      .then(r => r.json()).then(d => {
        const list = (d.buyers || d || []).map((b: Record<string, string>) => ({ id: b._id || b.id, name: b.buyerName || b.company || "Unknown" }));
        setBuyerOptions(list);
      }).catch(() => {});
    // Fetch suppliers for purchase filter
    fetch(`${API_URL}/api/business-tools/suppliers?limit=200`, { headers: h })
      .then(r => r.json()).then(d => {
        const list = (d.suppliers || d || []).map((s: Record<string, string>) => ({ id: s._id || s.id, name: s.name || s.supplierName || "Unknown" }));
        setSupplierOptions(list);
      }).catch(() => {});
    // Fetch products for stock movement filter
    fetch(`${API_URL}/api/business-tools/inventory?limit=200`, { headers: h })
      .then(r => r.json()).then(d => {
        const list = (d.listings || d || []).map((p: Record<string, string>) => ({ id: p._id || p.id, name: p.productName || "Unknown" }));
        setProductOptions(list);
      }).catch(() => {});
  }, [token]);

  // Fetch buyer transactions (buyer ledger drill-down)
  const fetchBuyerTransactions = async (bId: string) => {
    if (!token) return;
    setLoadingTransactions(true);
    setSelectedBuyer(bId);
    try {
      const dateParams = `startDate=${new Date(startDate).toISOString()}&endDate=${new Date(endDate).toISOString()}`;
      const res = await fetch(`${API_URL}/api/business-tools/reports/buyer-ledger/${bId}/transactions?${dateParams}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBuyerTransactions(await res.json());
    } catch { setBuyerTransactions(null); }
    setLoadingTransactions(false);
  };

  // ── Export handler ──
  const handleExport = async (format: "csv" | "xlsx") => {
    if (!token) return;
    setExporting(true);
    try {
      const exportType = TAB_EXPORT_MAP[tab];
      const dateParams = `startDate=${new Date(startDate).toISOString()}&endDate=${new Date(endDate).toISOString()}`;
      const url = `${API_URL}/api/business-tools/export/${exportType}?format=${format}&${dateParams}&period=${period}`;
      const res = await fetch(url, { headers: authHeaders() });
      if (!res.ok) { alert("Export failed"); setExporting(false); return; }
      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${exportType}-report.${format}`;
      a.click();
      URL.revokeObjectURL(downloadUrl);
    } catch { alert("Export failed"); }
    setExporting(false);
  };

  // ── Import handlers ──
  const downloadTemplate = async (type: ImportType, format: "csv" | "xlsx" = "xlsx") => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/import/template/${type}?format=${format}`, { headers: authHeaders() });
      if (!res.ok) { alert("Failed to download template"); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}-import-template.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { alert("Failed"); }
  };

  const validateImport = async () => {
    if (!importFile) return;
    setImportValidating(true);
    try {
      const form = new FormData();
      form.append("file", importFile);
      form.append("data_type", importType);
      const res = await fetch(`${API_URL}/api/business-tools/import/validate`, { method: "POST", headers: authHeaders(), body: form });
      const data = await res.json();
      setImportValidation(data);
      setImportStep("preview");
    } catch { alert("Validation failed"); }
    setImportValidating(false);
  };

  const processImport = async () => {
    if (!importFile) return;
    setImportProcessing(true);
    try {
      const form = new FormData();
      form.append("file", importFile);
      form.append("data_type", importType);
      const res = await fetch(`${API_URL}/api/business-tools/import/process`, { method: "POST", headers: authHeaders(), body: form });
      const data = await res.json();
      setImportResult(data);
      setImportStep("result");
    } catch { alert("Import failed"); }
    setImportProcessing(false);
  };

  const resetImport = () => {
    setShowImport(false); setImportStep("select"); setImportFile(null);
    setImportValidation(null); setImportResult(null);
  };

  const maxSales = Math.max(...(salesData.periods.map(p => p.totalSales) || [1]), 1);
  const maxProductRev = Math.max(...(productData.map(p => p.totalRevenue) || [1]), 1);

  const tabs: { key: Tab; label: string; icon: typeof BarChart3 }[] = [
    { key: "outstanding", label: "Outstanding", icon: Clock },
    { key: "purchase", label: "Purchase", icon: ShoppingCart },
    { key: "stock-movement", label: "Stock Movement", icon: ArrowLeftRight },
    { key: "buyer-ledger", label: "Buyer Ledger", icon: BookOpen },
    { key: "product-perf", label: "Product Perf.", icon: Zap },
    { key: "category", label: "Category", icon: FolderOpen },
    { key: "low-stock", label: "Low Stock", icon: AlertTriangle },
    { key: "sales", label: "Sales", icon: TrendingUp },
    { key: "profit", label: "Profit", icon: DollarSign },
    { key: "product-profit", label: "Product Profit", icon: PieChart },
    { key: "inventory-value", label: "Inventory Value", icon: Package },
    { key: "products", label: "Products", icon: BarChart3 },
    { key: "inventory", label: "Stock Status", icon: Package },
    { key: "buyers", label: "Top Buyers", icon: Users }
  ];

  if (!hasPermission("view_reports")) {
    return <div className="p-6 text-center text-gray-500" data-testid="no-permission">You do not have permission to view reports.</div>;
  }

  const needsDateFilter = !["inventory", "inventory-value"].includes(tab);
  const needsPeriodFilter = ["sales", "profit"].includes(tab);
  const needsEntityFilter = ["outstanding", "purchase", "stock-movement", "buyer-ledger"].includes(tab);

  return (
    <div className="space-y-6" data-testid="reports-page">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Reports</h1>
          <p className="text-sm text-gray-500 mt-1">Business analytics, exports & data import</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Export Buttons */}
          <button onClick={() => handleExport("csv")} disabled={exporting || loading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 disabled:opacity-50" data-testid="export-csv-btn">
            <FileText className="w-4 h-4" /> Export CSV
          </button>
          <button onClick={() => handleExport("xlsx")} disabled={exporting || loading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 disabled:opacity-50" data-testid="export-excel-btn">
            <FileSpreadsheet className="w-4 h-4 text-green-600" /> Export Excel
          </button>
          <button onClick={() => { setShowImport(true); setImportStep("select"); }}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700" data-testid="import-data-btn">
            <Upload className="w-4 h-4" /> Import Data
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg overflow-x-auto">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); setReportPage(1); }}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${tab === t.key ? "bg-white text-indigo-600 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
            data-testid={`tab-${t.key}`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      {needsDateFilter && (
        <div className="flex items-center gap-3 flex-wrap" data-testid="report-filters">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="start-date" />
            <span className="text-gray-400">to</span>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="end-date" />
          </div>
          {needsPeriodFilter && (
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <select value={period} onChange={e => setPeriod(e.target.value)}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="period-select">
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
              </select>
            </div>
          )}
          {needsEntityFilter && (
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-gray-400" />
              {tab === "outstanding" && (
                <select value={buyerFilter} onChange={e => { setBuyerFilter(e.target.value); setReportPage(1); }}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="buyer-filter">
                  <option value="">All Buyers</option>
                  {buyerOptions.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              )}
              {tab === "buyer-ledger" && (
                <select value={buyerFilter} onChange={e => { setBuyerFilter(e.target.value); setReportPage(1); }}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="buyer-ledger-filter">
                  <option value="">All Buyers</option>
                  {buyerOptions.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              )}
              {tab === "purchase" && (
                <select value={supplierFilter} onChange={e => { setSupplierFilter(e.target.value); setReportPage(1); }}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="supplier-filter">
                  <option value="">All Suppliers</option>
                  {supplierOptions.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              )}
              {tab === "stock-movement" && (
                <select value={productFilter} onChange={e => { setProductFilter(e.target.value); setReportPage(1); }}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm" data-testid="product-filter">
                  <option value="">All Products</option>
                  {productOptions.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              )}
            </div>
          )}
          {exporting && <span className="text-xs text-blue-600 flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Exporting...</span>}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading report...</div>
      ) : (
        <>
          {/* Sales Tab */}
          {tab === "sales" && (
            <div className="space-y-6" data-testid="sales-report">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Revenue", value: salesData.overall.totalRevenue || 0, prefix: true },
                  { label: "Total GST", value: salesData.overall.totalGst || 0, prefix: true },
                  { label: "Total Invoices", value: salesData.overall.invoiceCount || 0, prefix: false },
                  { label: "Avg Invoice", value: salesData.overall.avgInvoiceValue || 0, prefix: true }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`stat-card-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className="text-xl font-bold text-gray-900 mt-1 flex items-center gap-1">
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>
              {salesData.periods.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 p-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">{period === "monthly" ? "Monthly" : "Quarterly"} Sales</h3>
                  <div className="space-y-3">
                    {salesData.periods.map((p, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs text-gray-500 w-20 shrink-0">{p.label}</span>
                        <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                          <div className="bg-indigo-500 h-full rounded-full flex items-center justify-end pr-2 transition-all" style={{ width: `${Math.max((p.totalSales / maxSales) * 100, 5)}%` }}>
                            <span className="text-[10px] text-white font-medium whitespace-nowrap">{p.totalSales.toLocaleString("en-IN", { minimumFractionDigits: 0 })}</span>
                          </div>
                        </div>
                        <span className="text-xs text-gray-400 w-12 text-right">{p.invoiceCount} inv</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No sales data for the selected period</div>}
            </div>
          )}

          {/* Profit Summary Tab */}
          {tab === "profit" && (
            <div className="space-y-6" data-testid="profit-report">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Revenue", value: profitData.overall?.totalRevenue || 0, color: "text-gray-900" },
                  { label: "Total Cost", value: profitData.overall?.totalCost || 0, color: "text-amber-600" },
                  { label: "Total Profit", value: profitData.overall?.totalProfit || 0, color: "text-green-600" },
                  { label: "Profit Margin", value: `${(profitData.overall?.profitMargin || 0).toFixed(1)}%`, color: "text-indigo-600", noPrefix: true }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`profit-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {!card.noPrefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : card.value}
                    </p>
                  </div>
                ))}
              </div>
              {(profitData.periods?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 p-6">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">{period === "monthly" ? "Monthly" : "Quarterly"} Profit</h3>
                  <div className="space-y-3">
                    {profitData.periods.map((p, i) => {
                      const maxRev = Math.max(...profitData.periods.map(pp => pp.revenue), 1);
                      return (
                        <div key={i} className="flex items-center gap-3">
                          <span className="text-xs text-gray-500 w-20 shrink-0">{p.label}</span>
                          <div className="flex-1">
                            <div className="relative bg-gray-100 rounded-full h-6 overflow-hidden">
                              <div className="bg-green-500 h-full rounded-full transition-all" style={{ width: `${Math.max((p.revenue / maxRev) * 100, 5)}%` }} />
                              <div className="absolute inset-0 flex items-center justify-end pr-2">
                                <span className="text-[10px] font-medium text-gray-700">Profit: {p.profit.toLocaleString("en-IN")} ({p.margin.toFixed(1)}%)</span>
                              </div>
                            </div>
                          </div>
                          <span className="text-xs text-gray-400 w-16 text-right">{p.totalQuantity} units</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No profit data for the selected period</div>}
            </div>
          )}

          {/* Product Profit Tab */}
          {tab === "product-profit" && (
            <div data-testid="product-profit-report">
              {productProfitData.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                        <th className="text-left px-4 py-3">#</th><th className="text-left px-4 py-3">Product</th>
                        <th className="text-right px-4 py-3">Qty Sold</th><th className="text-right px-4 py-3">Revenue</th>
                        <th className="text-right px-4 py-3">Cost</th><th className="text-right px-4 py-3">Profit</th><th className="text-right px-4 py-3">Margin</th>
                      </tr>
                    </thead>
                    <tbody>
                      {productProfitData.map((p, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                          <td className="px-4 py-3 font-medium text-gray-700">{p.productName}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{p.totalQuantity}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{p.totalRevenue.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right text-amber-600">{p.totalCost.toLocaleString("en-IN")}</td>
                          <td className={`px-4 py-3 text-right font-medium ${p.profit >= 0 ? "text-green-600" : "text-red-600"}`}>{p.profit.toLocaleString("en-IN")}</td>
                          <td className={`px-4 py-3 text-right ${p.margin >= 0 ? "text-green-600" : "text-red-600"}`}>{p.margin.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No product profit data for the selected period</div>}
            </div>
          )}

          {/* Inventory Value Tab */}
          {tab === "inventory-value" && (
            <div className="space-y-6" data-testid="inventory-value-report">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Inventory Value", value: inventoryValueData.summary?.totalInventoryValue || 0, color: "text-gray-900" },
                  { label: "Potential Revenue", value: inventoryValueData.summary?.totalPotentialRevenue || 0, color: "text-indigo-600" },
                  { label: "Potential Profit", value: inventoryValueData.summary?.totalPotentialProfit || 0, color: "text-green-600" },
                  { label: "Total Items", value: inventoryValueData.summary?.totalItems || 0, color: "text-gray-900", noPrefix: true }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`inv-val-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {!card.noPrefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.noPrefix ? {} : { minimumFractionDigits: 2 }) : card.value}
                    </p>
                  </div>
                ))}
              </div>
              {(inventoryValueData.items?.length || 0) > 0 && (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                        <th className="text-left px-4 py-3">Product</th><th className="text-center px-4 py-3">Type</th>
                        <th className="text-right px-4 py-3">Stock</th><th className="text-right px-4 py-3">Purchase Price</th>
                        <th className="text-right px-4 py-3">Selling Price</th><th className="text-right px-4 py-3">Stock Value</th>
                        <th className="text-right px-4 py-3">Potential Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inventoryValueData.items.map((item, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-700">{item.productName || "N/A"}</td>
                          <td className="px-4 py-3 text-center">
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${item.productType === "composite" ? "bg-indigo-50 text-indigo-600" : "bg-gray-100 text-gray-600"}`}>
                              {item.productType === "composite" ? "Composite" : "Single"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">{item.stock}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{item.purchase_price ? `${item.purchase_price.toLocaleString("en-IN")}` : "-"}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{item.selling_price ? `${item.selling_price.toLocaleString("en-IN")}` : "-"}</td>
                          <td className="px-4 py-3 text-right font-medium text-amber-600">{item.stockValue.toLocaleString("en-IN")}</td>
                          <td className="px-4 py-3 text-right font-medium text-green-600">{item.potentialRevenue.toLocaleString("en-IN")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Products Tab */}
          {tab === "products" && (
            <div data-testid="products-report">
              {productData.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">#</th>
                          <th className="text-left px-4 py-3">Product</th>
                          <th className="text-left px-4 py-3">HSN</th>
                          <th className="text-right px-4 py-3">Qty</th>
                          <th className="text-right px-4 py-3">Taxable</th>
                          <th className="text-right px-4 py-3">GST %</th>
                          <th className="text-right px-4 py-3">GST Amt</th>
                          <th className="text-right px-4 py-3">Total</th>
                          <th className="px-4 py-3 w-24">Chart</th>
                        </tr>
                      </thead>
                      <tbody>
                        {productData.map((p, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                            <td className="px-4 py-3 font-medium text-gray-700">{p.productName}</td>
                            <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.hsnCode || "-"}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{p.totalQuantity}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{(p.taxableValue ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{p.gstPercent ?? 0}%</td>
                            <td className="px-4 py-3 text-right text-gray-600">{(p.totalGst ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right font-medium flex items-center justify-end gap-0.5">
                              <IndianRupee className="w-3.5 h-3.5" />{p.totalRevenue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                            </td>
                            <td className="px-4 py-3">
                              <div className="bg-gray-100 rounded-full h-3 w-full">
                                <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${(p.totalRevenue / maxProductRev) * 100}%` }} />
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No product sales data for the selected period</div>}
            </div>
          )}

          {/* Inventory Stock Status Tab */}
          {tab === "inventory" && (
            <div className="space-y-6" data-testid="inventory-report">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Products", value: inventoryData.summary.totalItems || 0, color: "text-gray-900" },
                  { label: "Total Stock Units", value: inventoryData.summary.totalStockUnits || 0, color: "text-gray-900" },
                  { label: "Low Stock", value: inventoryData.summary.lowStock || 0, color: "text-amber-600" },
                  { label: "Out of Stock", value: inventoryData.summary.outOfStock || 0, color: "text-red-600" }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`inv-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 ${card.color}`}>{card.value}</p>
                  </div>
                ))}
              </div>
              {inventoryData.items.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                        <th className="text-left px-4 py-3">Product</th><th className="text-right px-4 py-3">Stock</th>
                        <th className="text-right px-4 py-3">Alert Level</th><th className="text-center px-4 py-3">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inventoryData.items.map((item, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-700">{item.productName || "N/A"}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{item.stock}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{item.lowStockAlert}</td>
                          <td className="px-4 py-3 text-center">
                            {item.stock === 0 ? (
                              <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-medium">Out of Stock</span>
                            ) : item.isLowStock ? (
                              <span className="text-xs bg-amber-50 text-amber-600 px-2 py-0.5 rounded-full font-medium">Low Stock</span>
                            ) : (
                              <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full font-medium">In Stock</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Top Buyers Tab */}
          {tab === "buyers" && (
            <div data-testid="buyers-report">
              {buyerData.length > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                        <th className="text-left px-4 py-3">#</th><th className="text-left px-4 py-3">Buyer</th>
                        <th className="text-left px-4 py-3">Company</th><th className="text-right px-4 py-3">Total Spent</th>
                        <th className="text-right px-4 py-3">Invoices</th><th className="text-right px-4 py-3">Last Order</th>
                      </tr>
                    </thead>
                    <tbody>
                      {buyerData.map((b, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                          <td className="px-4 py-3 font-medium text-gray-700">{b.buyerName}</td>
                          <td className="px-4 py-3 text-gray-500">{b.company || "-"}</td>
                          <td className="px-4 py-3 text-right font-medium flex items-center justify-end gap-0.5">
                            <IndianRupee className="w-3.5 h-3.5" />{b.totalSpent.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-700">{b.invoiceCount}</td>
                          <td className="px-4 py-3 text-right text-gray-500">{b.lastInvoiceDate ? new Date(b.lastInvoiceDate).toLocaleDateString("en-IN") : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No buyer data for the selected period</div>}
            </div>
          )}

          {/* ═══ OUTSTANDING / RECEIVABLES TAB ═══ */}
          {tab === "outstanding" && (
            <div className="space-y-6" data-testid="outstanding-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Receivable", value: outstandingData.summary?.totalReceivable || 0, color: "text-red-600", prefix: true },
                  { label: "Overdue Amount", value: outstandingData.summary?.overdueAmount || 0, color: "text-amber-600", prefix: true },
                  { label: "Total Buyers", value: outstandingData.summary?.totalBuyers || 0, color: "text-gray-900", prefix: false },
                  { label: "Unpaid Invoices", value: outstandingData.summary?.totalInvoices || 0, color: "text-gray-900", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`outstanding-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Aging Buckets */}
              {outstandingData.aging?.buckets && Object.keys(outstandingData.aging.buckets).length > 0 && (
                <div className="bg-white rounded-xl border border-gray-100 p-5">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Aging Analysis</h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {[
                      { key: "current", label: "Current", color: "bg-green-50 text-green-700 border-green-200" },
                      { key: "0-30", label: "0-30 Days", color: "bg-blue-50 text-blue-700 border-blue-200" },
                      { key: "31-60", label: "31-60 Days", color: "bg-yellow-50 text-yellow-700 border-yellow-200" },
                      { key: "61-90", label: "61-90 Days", color: "bg-orange-50 text-orange-700 border-orange-200" },
                      { key: "90+", label: "90+ Days", color: "bg-red-50 text-red-700 border-red-200" }
                    ].map(b => (
                      <div key={b.key} className={`rounded-lg border p-3 ${b.color}`} data-testid={`aging-${b.key}`}>
                        <p className="text-xs font-medium opacity-75">{b.label}</p>
                        <p className="text-lg font-bold flex items-center gap-0.5">
                          <IndianRupee className="w-3.5 h-3.5" />
                          {(outstandingData.aging.buckets[b.key] || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </p>
                        <p className="text-[10px] opacity-60">{outstandingData.aging.counts?.[b.key] || 0} invoices</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Table */}
              {(outstandingData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">Invoice #</th>
                          <th className="text-left px-4 py-3">Buyer</th>
                          <th className="text-right px-4 py-3">Invoice Date</th>
                          <th className="text-right px-4 py-3">Due Date</th>
                          <th className="text-right px-4 py-3">Total</th>
                          <th className="text-right px-4 py-3">Paid</th>
                          <th className="text-right px-4 py-3">Pending</th>
                          <th className="text-right px-4 py-3">Overdue</th>
                          <th className="text-center px-4 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {outstandingData.items.map((item, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 font-mono text-xs text-indigo-600">{item.invoiceNumber}</td>
                            <td className="px-4 py-3">
                              <p className="font-medium text-gray-700 text-xs">{item.buyerName}</p>
                              {item.company && <p className="text-[10px] text-gray-400">{item.company}</p>}
                            </td>
                            <td className="px-4 py-3 text-right text-gray-500 text-xs">{item.invoiceDate ? new Date(item.invoiceDate).toLocaleDateString("en-IN") : "-"}</td>
                            <td className="px-4 py-3 text-right text-gray-500 text-xs">{item.dueDate ? new Date(item.dueDate).toLocaleDateString("en-IN") : "-"}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{item.totalAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right text-green-600">{item.paidAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right font-medium text-red-600">{item.pendingAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right">
                              <span className={`text-xs font-medium ${item.daysOverdue > 60 ? "text-red-600" : item.daysOverdue > 30 ? "text-amber-600" : item.daysOverdue > 0 ? "text-blue-600" : "text-green-600"}`}>
                                {item.daysOverdue > 0 ? `${item.daysOverdue}d` : "On time"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${item.status === "Partial" ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"}`}>
                                {item.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Pagination */}
                  {outstandingData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {outstandingData.pagination.page} of {outstandingData.pagination.pages} ({outstandingData.pagination.total} items)</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="outstanding-prev-page"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(outstandingData.pagination.pages, p + 1))} disabled={reportPage >= outstandingData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="outstanding-next-page"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No outstanding receivables found</div>}
            </div>
          )}

          {/* ═══ PURCHASE REPORT TAB ═══ */}
          {tab === "purchase" && (
            <div className="space-y-6" data-testid="purchase-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Purchase Value", value: purchaseData.summary?.totalPurchaseValue || 0, color: "text-gray-900", prefix: true },
                  { label: "Total Items Ordered", value: purchaseData.summary?.totalQuantity || 0, color: "text-indigo-600", prefix: false },
                  { label: "Avg Order Value", value: purchaseData.summary?.avgOrderValue || 0, color: "text-blue-600", prefix: true },
                  { label: "Total Suppliers", value: purchaseData.summary?.totalSuppliers || 0, color: "text-gray-900", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`purchase-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Table */}
              {(purchaseData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">PO Number</th>
                          <th className="text-left px-4 py-3">Supplier</th>
                          <th className="text-left px-4 py-3">Products</th>
                          <th className="text-center px-4 py-3">Status</th>
                          <th className="text-right px-4 py-3">Amount</th>
                          <th className="text-right px-4 py-3">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {purchaseData.items.map((item, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 font-mono text-xs text-indigo-600">{item.poNumber}</td>
                            <td className="px-4 py-3">
                              <p className="font-medium text-gray-700 text-xs">{item.supplierName}</p>
                              {item.supplierPhone && <p className="text-[10px] text-gray-400">{item.supplierPhone}</p>}
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">{item.productNames || "-"}</td>
                            <td className="px-4 py-3 text-center">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                item.status === "received" ? "bg-green-50 text-green-600" :
                                item.status === "sent" ? "bg-blue-50 text-blue-600" :
                                "bg-amber-50 text-amber-600"
                              }`}>{item.status}</span>
                            </td>
                            <td className="px-4 py-3 text-right font-medium text-gray-700">{item.totalAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right text-gray-500 text-xs">{item.createdAt ? new Date(item.createdAt).toLocaleDateString("en-IN") : "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Pagination */}
                  {purchaseData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {purchaseData.pagination.page} of {purchaseData.pagination.pages} ({purchaseData.pagination.total} items)</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="purchase-prev-page"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(purchaseData.pagination.pages, p + 1))} disabled={reportPage >= purchaseData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="purchase-next-page"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No purchase orders found for the selected period</div>}
            </div>
          )}

          {/* ═══ STOCK MOVEMENT TAB ═══ */}
          {tab === "stock-movement" && (
            <div className="space-y-6" data-testid="stock-movement-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Inward", value: stockMovementData.summary?.totalInward || 0, color: "text-green-600", prefix: false },
                  { label: "Total Outward", value: stockMovementData.summary?.totalOutward || 0, color: "text-red-600", prefix: false },
                  { label: "Net Movement", value: stockMovementData.summary?.netMovement || 0, color: (stockMovementData.summary?.netMovement || 0) >= 0 ? "text-green-600" : "text-red-600", prefix: false },
                  { label: "Products Tracked", value: stockMovementData.summary?.totalProducts || 0, color: "text-gray-900", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`stock-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 ${card.color}`}>{typeof card.value === "number" ? card.value.toLocaleString("en-IN") : card.value}</p>
                  </div>
                ))}
              </div>

              {/* Table */}
              {(stockMovementData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">Product Name</th>
                          <th className="text-right px-4 py-3">Opening</th>
                          <th className="text-right px-4 py-3">Inward</th>
                          <th className="text-right px-4 py-3">Outward</th>
                          <th className="text-right px-4 py-3">Adjustment</th>
                          <th className="text-right px-4 py-3">Closing</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stockMovementData.items.map((item, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 font-medium text-gray-700">{item.productName}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.openingStock}</td>
                            <td className="px-4 py-3 text-right text-green-600 font-medium">{item.inward > 0 ? `+${item.inward}` : item.inward}</td>
                            <td className="px-4 py-3 text-right text-red-600 font-medium">{item.outward > 0 ? `-${item.outward}` : item.outward}</td>
                            <td className={`px-4 py-3 text-right font-medium ${item.adjustment >= 0 ? "text-blue-600" : "text-amber-600"}`}>
                              {item.adjustment > 0 ? `+${item.adjustment}` : item.adjustment}
                            </td>
                            <td className="px-4 py-3 text-right font-bold text-gray-900">{item.closingStock}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Pagination */}
                  {stockMovementData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {stockMovementData.pagination.page} of {stockMovementData.pagination.pages} ({stockMovementData.pagination.total} items)</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="stock-prev-page"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(stockMovementData.pagination.pages, p + 1))} disabled={reportPage >= stockMovementData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30" data-testid="stock-next-page"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No stock movement data for the selected period</div>}
            </div>
          )}

          {/* ═══ BUYER LEDGER TAB ═══ */}
          {tab === "buyer-ledger" && (
            <div className="space-y-6" data-testid="buyer-ledger-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Sales", value: buyerLedgerData.summary?.totalSales || 0, color: "text-gray-900", prefix: true },
                  { label: "Total Paid", value: buyerLedgerData.summary?.totalPaid || 0, color: "text-green-600", prefix: true },
                  { label: "Total Pending", value: buyerLedgerData.summary?.totalPending || 0, color: "text-red-600", prefix: true },
                  { label: "Total Buyers", value: buyerLedgerData.summary?.totalBuyers || 0, color: "text-gray-900", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`ledger-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Transaction Detail Modal */}
              {selectedBuyer && buyerTransactions && (
                <div className="bg-white rounded-xl border-2 border-indigo-200 p-5 space-y-4" data-testid="buyer-transactions">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700">Transaction History: {buyerTransactions.buyer?.buyerName}</h3>
                      {buyerTransactions.buyer?.company && <p className="text-xs text-gray-400">{buyerTransactions.buyer.company}</p>}
                    </div>
                    <button onClick={() => { setSelectedBuyer(null); setBuyerTransactions(null); }}
                      className="text-gray-400 hover:text-gray-600 p-1" data-testid="close-transactions"><X className="w-4 h-4" /></button>
                  </div>
                  {loadingTransactions ? <div className="text-center py-4 text-gray-400 text-sm">Loading...</div> : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                            <th className="text-left px-3 py-2">Invoice #</th><th className="text-right px-3 py-2">Date</th>
                            <th className="text-right px-3 py-2">Amount</th><th className="text-right px-3 py-2">Paid</th>
                            <th className="text-right px-3 py-2">Pending</th><th className="text-center px-3 py-2">Status</th>
                            <th className="text-left px-3 py-2">Products</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(buyerTransactions.transactions || []).map((t, i) => (
                            <tr key={i} className="border-b border-gray-50">
                              <td className="px-3 py-2 font-mono text-xs text-indigo-600">{t.invoiceNumber}</td>
                              <td className="px-3 py-2 text-right text-xs text-gray-500">{t.date ? new Date(t.date).toLocaleDateString("en-IN") : "-"}</td>
                              <td className="px-3 py-2 text-right">{t.totalAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                              <td className="px-3 py-2 text-right text-green-600">{t.paidAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                              <td className="px-3 py-2 text-right text-red-600">{t.pendingAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                              <td className="px-3 py-2 text-center">
                                <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${t.status === "paid" ? "bg-green-50 text-green-600" : t.status === "partially_paid" ? "bg-amber-50 text-amber-600" : "bg-gray-100 text-gray-600"}`}>{t.status}</span>
                              </td>
                              <td className="px-3 py-2 text-xs text-gray-500 max-w-[150px] truncate">{t.products || "-"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Buyer Ledger Table */}
              {(buyerLedgerData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">Buyer</th>
                          <th className="text-right px-4 py-3">Total Sales</th>
                          <th className="text-right px-4 py-3">Total Paid</th>
                          <th className="text-right px-4 py-3">Pending</th>
                          <th className="text-right px-4 py-3">Invoices</th>
                          <th className="text-right px-4 py-3">Last Invoice</th>
                          <th className="text-right px-4 py-3">Last Payment</th>
                          <th className="text-center px-4 py-3">Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {buyerLedgerData.items.map((item, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3">
                              <p className="font-medium text-gray-700 text-xs">{item.buyerName}</p>
                              {item.company && <p className="text-[10px] text-gray-400">{item.company}</p>}
                            </td>
                            <td className="px-4 py-3 text-right font-medium text-gray-700">{item.totalSales?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right text-green-600">{item.totalPaid?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right font-medium text-red-600">{item.pendingAmount?.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.invoiceCount}</td>
                            <td className="px-4 py-3 text-right text-gray-500 text-xs">{item.lastInvoiceDate ? new Date(item.lastInvoiceDate).toLocaleDateString("en-IN") : "-"}</td>
                            <td className="px-4 py-3 text-right text-gray-500 text-xs">{item.lastPaymentDate ? new Date(item.lastPaymentDate).toLocaleDateString("en-IN") : "-"}</td>
                            <td className="px-4 py-3 text-center">
                              <button onClick={() => fetchBuyerTransactions(item.buyerId)}
                                className="text-xs px-2 py-1 rounded bg-indigo-50 text-indigo-600 hover:bg-indigo-100 font-medium" data-testid={`view-transactions-${i}`}>
                                View
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {buyerLedgerData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {buyerLedgerData.pagination.page} of {buyerLedgerData.pagination.pages} ({buyerLedgerData.pagination.total} items)</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(buyerLedgerData.pagination.pages, p + 1))} disabled={reportPage >= buyerLedgerData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No buyer ledger data for the selected period</div>}
            </div>
          )}

          {/* ═══ PRODUCT PERFORMANCE TAB ═══ */}
          {tab === "product-perf" && (
            <div className="space-y-6" data-testid="product-perf-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Products", value: productPerfData.summary?.totalProducts || 0, color: "text-gray-900", prefix: false },
                  { label: "Total Revenue", value: productPerfData.summary?.totalRevenue || 0, color: "text-indigo-600", prefix: true },
                  { label: "Total Profit", value: productPerfData.summary?.totalProfit || 0, color: "text-green-600", prefix: true },
                  { label: "Avg Profit %", value: `${productPerfData.summary?.avgProfitPercent || 0}%`, color: "text-blue-600", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`perf-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Top Selling & Slow Moving */}
              <div className="grid md:grid-cols-2 gap-4">
                {productPerfData.topSelling?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="top-selling">
                    <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center gap-1.5"><TrendingUp className="w-4 h-4" /> Top Selling</h3>
                    <div className="space-y-2">
                      {productPerfData.topSelling.map((p, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-gray-700 font-medium truncate max-w-[60%]">{i + 1}. {p.productName}</span>
                          <span className="text-green-600 font-medium">{p.revenue.toLocaleString("en-IN")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {productPerfData.slowMoving?.length > 0 && (
                  <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="slow-moving">
                    <h3 className="text-sm font-semibold text-amber-700 mb-3 flex items-center gap-1.5"><AlertTriangle className="w-4 h-4" /> Slow Moving</h3>
                    <div className="space-y-2">
                      {productPerfData.slowMoving.map((p, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-gray-700 font-medium truncate max-w-[60%]">{i + 1}. {p.productName}</span>
                          <span className="text-amber-600 font-medium">{p.quantitySold} sold</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Full Table */}
              {(productPerfData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">#</th>
                          <th className="text-left px-4 py-3">Product Name</th>
                          <th className="text-left px-4 py-3">HSN</th>
                          <th className="text-right px-4 py-3">Qty Sold</th>
                          <th className="text-right px-4 py-3">Revenue</th>
                          <th className="text-right px-4 py-3">Profit</th>
                          <th className="text-right px-4 py-3">Profit %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {productPerfData.items.map((p, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                            <td className="px-4 py-3 font-medium text-gray-700">{p.productName}</td>
                            <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.hsnCode || "-"}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{p.quantitySold}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{p.revenue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className={`px-4 py-3 text-right font-medium ${p.profit >= 0 ? "text-green-600" : "text-red-600"}`}>{p.profit.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className={`px-4 py-3 text-right ${p.profitPercent >= 0 ? "text-green-600" : "text-red-600"}`}>{p.profitPercent}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {productPerfData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {productPerfData.pagination.page} of {productPerfData.pagination.pages}</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(productPerfData.pagination.pages, p + 1))} disabled={reportPage >= productPerfData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No product performance data for the selected period</div>}
            </div>
          )}

          {/* ═══ CATEGORY REPORT TAB ═══ */}
          {tab === "category" && (
            <div className="space-y-6" data-testid="category-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Categories", value: categoryData.summary?.totalCategories || 0, color: "text-gray-900", prefix: false },
                  { label: "Total Revenue", value: categoryData.summary?.totalRevenue || 0, color: "text-indigo-600", prefix: true },
                  { label: "Total Profit", value: categoryData.summary?.totalProfit || 0, color: "text-green-600", prefix: true },
                  { label: "Top Category", value: categoryData.summary?.topCategory || "N/A", color: "text-blue-600", prefix: false }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`cat-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 flex items-center gap-1 ${card.color}`}>
                      {card.prefix && <IndianRupee className="w-4 h-4" />}
                      {typeof card.value === "number" ? card.value.toLocaleString("en-IN", card.prefix ? { minimumFractionDigits: 2 } : {}) : card.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Table */}
              {(categoryData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">#</th>
                          <th className="text-left px-4 py-3">Category Name</th>
                          <th className="text-right px-4 py-3">Total Sales (Qty)</th>
                          <th className="text-right px-4 py-3">Revenue</th>
                          <th className="text-right px-4 py-3">Profit</th>
                          <th className="text-right px-4 py-3">Profit %</th>
                        </tr>
                      </thead>
                      <tbody>
                        {categoryData.items.map((c, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                            <td className="px-4 py-3 font-medium text-gray-700">
                              <span className={c.categoryName === "Uncategorized" ? "italic text-gray-400" : ""}>{c.categoryName}</span>
                            </td>
                            <td className="px-4 py-3 text-right text-gray-700">{c.totalSales}</td>
                            <td className="px-4 py-3 text-right text-gray-700">{c.revenue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className={`px-4 py-3 text-right font-medium ${c.profit >= 0 ? "text-green-600" : "text-red-600"}`}>{c.profit.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                            <td className={`px-4 py-3 text-right ${c.profitPercent >= 0 ? "text-green-600" : "text-red-600"}`}>{c.profitPercent}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No category data for the selected period</div>}
            </div>
          )}

          {/* ═══ LOW STOCK ANALYTICS TAB ═══ */}
          {tab === "low-stock" && (
            <div className="space-y-6" data-testid="low-stock-report">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Total Products", value: lowStockData.summary?.totalProducts || 0, color: "text-gray-900" },
                  { label: "Low Stock", value: lowStockData.summary?.lowStockCount || 0, color: "text-amber-600" },
                  { label: "Out of Stock", value: lowStockData.summary?.outOfStockCount || 0, color: "text-red-600" },
                  { label: "Healthy", value: lowStockData.summary?.healthyCount || 0, color: "text-green-600" }
                ].map((card, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-4" data-testid={`lowstock-stat-${i}`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">{card.label}</p>
                    <p className={`text-xl font-bold mt-1 ${card.color}`}>{card.value}</p>
                  </div>
                ))}
              </div>

              {/* Table */}
              {(lowStockData.items?.length || 0) > 0 ? (
                <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                          <th className="text-left px-4 py-3">Product Name</th>
                          <th className="text-right px-4 py-3">Min Stock</th>
                          <th className="text-right px-4 py-3">Current Stock</th>
                          <th className="text-right px-4 py-3">Times Hit Low</th>
                          <th className="text-right px-4 py-3">Avg Consumption/Day</th>
                          <th className="text-right px-4 py-3">Days of Stock</th>
                          <th className="text-center px-4 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lowStockData.items.map((item, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="px-4 py-3 font-medium text-gray-700">{item.productName}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.minStock}</td>
                            <td className={`px-4 py-3 text-right font-medium ${item.isOutOfStock ? "text-red-600" : item.isLowStock ? "text-amber-600" : "text-gray-700"}`}>{item.currentStock}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.timesHitLow}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.avgConsumption}</td>
                            <td className="px-4 py-3 text-right text-gray-500">{item.daysOfStock >= 999 ? "∞" : item.daysOfStock}</td>
                            <td className="px-4 py-3 text-center">
                              {item.isOutOfStock ? (
                                <span className="text-xs bg-red-50 text-red-600 px-2 py-0.5 rounded-full font-medium">Out of Stock</span>
                              ) : item.isLowStock ? (
                                <span className="text-xs bg-amber-50 text-amber-600 px-2 py-0.5 rounded-full font-medium">Low Stock</span>
                              ) : (
                                <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full font-medium">Healthy</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {lowStockData.pagination?.pages > 1 && (
                    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
                      <span>Page {lowStockData.pagination.page} of {lowStockData.pagination.pages}</span>
                      <div className="flex gap-1">
                        <button onClick={() => setReportPage(p => Math.max(1, p - 1))} disabled={reportPage <= 1}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronLeft className="w-4 h-4" /></button>
                        <button onClick={() => setReportPage(p => Math.min(lowStockData.pagination.pages, p + 1))} disabled={reportPage >= lowStockData.pagination.pages}
                          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
                      </div>
                    </div>
                  )}
                </div>
              ) : <div className="text-center py-8 text-gray-400 text-sm">No stock data available</div>}
            </div>
          )}
        </>
      )}

      {/* ══════ IMPORT DATA MODAL ══════ */}
      {showImport && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4" data-testid="import-modal">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-auto">
            <div className="flex items-center justify-between p-5 border-b">
              <h2 className="text-lg font-semibold flex items-center gap-2"><Upload className="w-5 h-5 text-blue-600" /> Import Data</h2>
              <button onClick={resetImport} className="text-gray-400 hover:text-gray-600" data-testid="close-import-modal"><X className="w-5 h-5" /></button>
            </div>

            <div className="p-5">
              {/* ── Step 1: Select type & upload ── */}
              {importStep === "select" && (
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Select Data Type</label>
                    <div className="grid grid-cols-2 gap-2">
                      {(["products", "inventory", "suppliers", "buyers"] as ImportType[]).map(t => (
                        <button key={t} onClick={() => setImportType(t)}
                          className={`px-4 py-3 rounded-lg border text-sm font-medium text-left transition ${importType === t ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}
                          data-testid={`import-type-${t}`}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Download Template</label>
                    <div className="flex gap-2">
                      <button onClick={() => downloadTemplate(importType, "xlsx")} className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" data-testid="download-template-xlsx">
                        <FileSpreadsheet className="w-4 h-4 text-green-600" /> Download Excel Template
                      </button>
                      <button onClick={() => downloadTemplate(importType, "csv")} className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50" data-testid="download-template-csv">
                        <FileText className="w-4 h-4" /> Download CSV Template
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Upload File</label>
                    <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center hover:border-blue-300 transition">
                      <input type="file" accept=".csv,.xlsx,.xls" onChange={e => setImportFile(e.target.files?.[0] || null)}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" data-testid="import-file-input" />
                      <p className="text-xs text-gray-400 mt-2">CSV or Excel (.xlsx) files only</p>
                    </div>
                    {importFile && <p className="text-xs text-green-600 mt-1 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> {importFile.name} ({(importFile.size / 1024).toFixed(1)} KB)</p>}
                  </div>

                  <button onClick={validateImport} disabled={!importFile || importValidating}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium" data-testid="validate-import-btn">
                    {importValidating ? <><Loader2 className="w-4 h-4 animate-spin" /> Validating...</> : <><Eye className="w-4 h-4" /> Validate & Preview</>}
                  </button>
                </div>
              )}

              {/* ── Step 2: Preview ── */}
              {importStep === "preview" && importValidation && (
                <div className="space-y-4">
                  <div className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium ${importValidation.valid ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>
                    {importValidation.valid ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    {importValidation.valid ? `${importValidation.totalRows} rows validated successfully` : `${importValidation.errors?.length || 0} validation errors found`}
                  </div>

                  {importValidation.errors?.length > 0 && (
                    <div className="bg-red-50 rounded-lg p-3 max-h-32 overflow-auto">
                      <p className="text-xs font-semibold text-red-700 mb-1">Errors:</p>
                      {importValidation.errors.map((e: any, i: number) => (
                        <p key={i} className="text-xs text-red-600">Row {e.row}: {e.message}</p>
                      ))}
                    </div>
                  )}

                  {importValidation.preview?.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-2">Preview (first {Math.min(importValidation.preview.length, 10)} rows):</p>
                      <div className="overflow-x-auto border rounded-lg max-h-60 overflow-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-50 border-b">
                              {importValidation.headers?.map((h: string, i: number) => (
                                <th key={i} className="px-3 py-2 text-left text-gray-500 font-medium whitespace-nowrap">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {importValidation.preview.slice(0, 10).map((row: any, i: number) => (
                              <tr key={i} className="border-b border-gray-50">
                                {importValidation.headers?.map((h: string, j: number) => (
                                  <td key={j} className="px-3 py-1.5 text-gray-700 whitespace-nowrap">{row[h] || "-"}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 justify-end pt-2">
                    <button onClick={() => { setImportStep("select"); setImportValidation(null); }} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800" data-testid="back-to-select-btn">Back</button>
                    <button onClick={processImport} disabled={importProcessing || !importValidation.valid}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium" data-testid="confirm-import-btn">
                      {importProcessing ? <><Loader2 className="w-4 h-4 animate-spin" /> Importing...</> : <><CheckCircle2 className="w-4 h-4" /> Confirm Import ({importValidation.totalRows} rows)</>}
                    </button>
                  </div>
                </div>
              )}

              {/* ── Step 3: Result ── */}
              {importStep === "result" && importResult && (
                <div className="space-y-4">
                  <div className="bg-green-50 rounded-lg p-4 text-center">
                    <CheckCircle2 className="w-10 h-10 text-green-500 mx-auto mb-2" />
                    <p className="text-lg font-semibold text-green-700">Import Complete</p>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-2xl font-bold text-green-600">{importResult.imported}</p>
                      <p className="text-xs text-gray-500">Imported</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-2xl font-bold text-amber-600">{importResult.skipped}</p>
                      <p className="text-xs text-gray-500">Skipped</p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <p className="text-2xl font-bold text-gray-600">{importResult.total}</p>
                      <p className="text-xs text-gray-500">Total Rows</p>
                    </div>
                  </div>
                  {importResult.errors?.length > 0 && (
                    <div className="bg-amber-50 rounded-lg p-3 max-h-32 overflow-auto">
                      <p className="text-xs font-semibold text-amber-700 mb-1">Notes:</p>
                      {importResult.errors.map((e: string, i: number) => (
                        <p key={i} className="text-xs text-amber-600">{e}</p>
                      ))}
                    </div>
                  )}
                  <button onClick={resetImport} className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium" data-testid="close-import-result-btn">Done</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
