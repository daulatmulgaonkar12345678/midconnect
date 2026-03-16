"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import {
  BarChart3, TrendingUp, Package, Users, Calendar, Filter,
  IndianRupee, DollarSign, PieChart, Download, Upload, FileSpreadsheet,
  FileText, X, CheckCircle2, AlertCircle, Loader2, FileDown, Eye
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type Tab = "sales" | "profit" | "product-profit" | "inventory-value" | "products" | "inventory" | "buyers";

interface SalesPeriod { label: string; totalSales: number; totalGst: number; invoiceCount: number; avgInvoiceValue: number; }
interface ProfitPeriod { label: string; revenue: number; cost: number; profit: number; margin: number; invoiceCount: number; totalQuantity: number; }
interface ProductProfit { productName: string; totalQuantity: number; totalRevenue: number; totalCost: number; profit: number; margin: number; invoiceCount: number; }
interface InventoryValueItem { id: string; productName: string; productType: string; stock: number; purchase_price: number; selling_price: number; stockValue: number; potentialRevenue: number; }
interface ProductSale { productName: string; totalQuantity: number; totalRevenue: number; invoiceCount: number; }
interface InventoryItem { id: string; productName: string; stock: number; lowStockAlert: number; isLowStock: boolean; sku?: string; }
interface TopBuyer { buyerId: string; buyerName: string; company: string; totalSpent: number; invoiceCount: number; lastInvoiceDate?: string; }

const TAB_EXPORT_MAP: Record<Tab, string> = {
  sales: "sales", profit: "profit", "product-profit": "profit",
  "inventory-value": "inventory", products: "sales",
  inventory: "inventory", buyers: "buyers"
};

type ImportType = "products" | "inventory" | "suppliers" | "buyers";

export default function ReportsPage() {
  const { hasPermission, token } = usePermissions();
  const [tab, setTab] = useState<Tab>("sales");
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
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [token, tab, period, startDate, endDate]);

  useEffect(() => { fetchReport(); }, [fetchReport]);

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
          <button key={t.key} onClick={() => setTab(t.key)}
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
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-gray-500 text-xs uppercase border-b border-gray-100">
                        <th className="text-left px-4 py-3">#</th><th className="text-left px-4 py-3">Product</th>
                        <th className="text-right px-4 py-3">Qty Sold</th><th className="text-right px-4 py-3">Revenue</th><th className="px-4 py-3">Chart</th>
                      </tr>
                    </thead>
                    <tbody>
                      {productData.map((p, i) => (
                        <tr key={i} className="border-b border-gray-50">
                          <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                          <td className="px-4 py-3 font-medium text-gray-700">{p.productName}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{p.totalQuantity}</td>
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
