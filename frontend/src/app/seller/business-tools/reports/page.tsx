"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import { BarChart3, TrendingUp, Package, Users, Calendar, Filter, IndianRupee, DollarSign, PieChart } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

type Tab = "sales" | "profit" | "product-profit" | "inventory-value" | "products" | "inventory" | "buyers";

interface SalesPeriod {
  label: string;
  totalSales: number;
  totalGst: number;
  invoiceCount: number;
  avgInvoiceValue: number;
}

interface ProfitPeriod {
  label: string;
  revenue: number;
  cost: number;
  profit: number;
  margin: number;
  invoiceCount: number;
  totalQuantity: number;
}

interface ProductProfit {
  productName: string;
  totalQuantity: number;
  totalRevenue: number;
  totalCost: number;
  profit: number;
  margin: number;
  invoiceCount: number;
}

interface InventoryValueItem {
  id: string;
  productName: string;
  productType: string;
  stock: number;
  purchase_price: number;
  selling_price: number;
  stockValue: number;
  potentialRevenue: number;
}

interface ProductSale {
  productName: string;
  totalQuantity: number;
  totalRevenue: number;
  invoiceCount: number;
}

interface InventoryItem {
  id: string;
  productName: string;
  stock: number;
  lowStockAlert: number;
  isLowStock: boolean;
  sku?: string;
}

interface TopBuyer {
  buyerId: string;
  buyerName: string;
  company: string;
  totalSpent: number;
  invoiceCount: number;
  lastInvoiceDate?: string;
}

export default function ReportsPage() {
  const { hasPermission, token } = usePermissions();
  const [tab, setTab] = useState<Tab>("sales");
  const [period, setPeriod] = useState("monthly");
  const [loading, setLoading] = useState(true);

  const [salesData, setSalesData] = useState<{ overall: Record<string, number>; periods: SalesPeriod[] }>({ overall: {}, periods: [] });
  const [profitData, setProfitData] = useState<{ overall: Record<string, number>; periods: ProfitPeriod[] }>({ overall: {}, periods: [] });
  const [productProfitData, setProductProfitData] = useState<ProductProfit[]>([]);
  const [inventoryValueData, setInventoryValueData] = useState<{ summary: Record<string, number>; items: InventoryValueItem[] }>({ summary: {}, items: [] });
  const [productData, setProductData] = useState<ProductSale[]>([]);
  const [inventoryData, setInventoryData] = useState<{ summary: Record<string, number>; items: InventoryItem[] }>({ summary: {}, items: [] });
  const [buyerData, setBuyerData] = useState<TopBuyer[]>([]);

  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 1); return d.toISOString().split("T")[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0]);

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
      <div>
        <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Reports</h1>
        <p className="text-sm text-gray-500 mt-1">Business analytics and insights</p>
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
                          <div className="bg-indigo-500 h-full rounded-full flex items-center justify-end pr-2 transition-all"
                            style={{ width: `${Math.max((p.totalSales / maxSales) * 100, 5)}%` }}>
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
                              <div className="bg-green-500 h-full rounded-full transition-all"
                                style={{ width: `${Math.max((p.revenue / maxRev) * 100, 5)}%` }}>
                              </div>
                              <div className="absolute inset-0 flex items-center justify-end pr-2">
                                <span className="text-[10px] font-medium text-gray-700">
                                  Profit: {p.profit.toLocaleString("en-IN")} ({p.margin.toFixed(1)}%)
                                </span>
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
                        <th className="text-left px-4 py-3">#</th>
                        <th className="text-left px-4 py-3">Product</th>
                        <th className="text-right px-4 py-3">Qty Sold</th>
                        <th className="text-right px-4 py-3">Revenue</th>
                        <th className="text-right px-4 py-3">Cost</th>
                        <th className="text-right px-4 py-3">Profit</th>
                        <th className="text-right px-4 py-3">Margin</th>
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
                          <td className={`px-4 py-3 text-right font-medium ${p.profit >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {p.profit.toLocaleString("en-IN")}
                          </td>
                          <td className={`px-4 py-3 text-right ${p.margin >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {p.margin.toFixed(1)}%
                          </td>
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
                        <th className="text-left px-4 py-3">Product</th>
                        <th className="text-center px-4 py-3">Type</th>
                        <th className="text-right px-4 py-3">Stock</th>
                        <th className="text-right px-4 py-3">Purchase Price</th>
                        <th className="text-right px-4 py-3">Selling Price</th>
                        <th className="text-right px-4 py-3">Stock Value</th>
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
                        <th className="text-left px-4 py-3">#</th>
                        <th className="text-left px-4 py-3">Product</th>
                        <th className="text-right px-4 py-3">Qty Sold</th>
                        <th className="text-right px-4 py-3">Revenue</th>
                        <th className="px-4 py-3">Chart</th>
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
                        <th className="text-left px-4 py-3">Product</th>
                        <th className="text-right px-4 py-3">Stock</th>
                        <th className="text-right px-4 py-3">Alert Level</th>
                        <th className="text-center px-4 py-3">Status</th>
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
                        <th className="text-left px-4 py-3">#</th>
                        <th className="text-left px-4 py-3">Buyer</th>
                        <th className="text-left px-4 py-3">Company</th>
                        <th className="text-right px-4 py-3">Total Spent</th>
                        <th className="text-right px-4 py-3">Invoices</th>
                        <th className="text-right px-4 py-3">Last Order</th>
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
    </div>
  );
}
