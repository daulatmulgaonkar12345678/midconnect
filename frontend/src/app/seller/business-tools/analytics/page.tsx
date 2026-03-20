'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from '../layout';
import {
  BarChart3, Loader2, Package2, TrendingUp, ShoppingCart, Layers, IndianRupee, Filter
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const CHART_COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2'];

interface Product { listingId: string; productName: string; sku: string; stock: number; minStock: number; }
interface SupplierFilter { supplierId: string; supplierName: string; }
interface Summary { totalOrders: number; totalQuantity: number; totalSpend: number; avgRate: number; supplierCount: number; currentStock: number; minStock: number; }
interface PriceTrendSupplier { supplierName: string; data: Array<{ period: string; avgRate: number }>; }
interface PurchaseTrend { period: string; quantity: number; amount: number; orders: number; }
interface StockPoint { date: string; stock: number; change: number; type: string; note: string; }
interface SupplierRate { supplierId: string; supplierName: string; rate: number; isBestPrice: boolean; }

const PERIODS = [
  { val: '7d', label: '7D' },
  { val: '30d', label: '30D' },
  { val: '3m', label: '3M' },
  { val: '6m', label: '6M' },
  { val: '1y', label: '1Y' },
  { val: 'custom', label: 'Custom' },
];

export default function AnalyticsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission, token, loading: permLoading } = usePermissions();
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [period, setPeriod] = useState('3m');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [loading, setLoading] = useState(true);
  const [chartLoading, setChartLoading] = useState(false);

  // Supplier filter
  const [suppliers, setSuppliers] = useState<SupplierFilter[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState<string>('');

  // Chart data
  const [summary, setSummary] = useState<Summary | null>(null);
  const [priceTrend, setPriceTrend] = useState<PriceTrendSupplier[]>([]);
  const [purchaseTrend, setPurchaseTrend] = useState<PurchaseTrend[]>([]);
  const [stockTrend, setStockTrend] = useState<{ data: StockPoint[]; currentStock: number; minStock: number }>({ data: [], currentStock: 0, minStock: 0 });
  const [supplierComparison, setSupplierComparison] = useState<SupplierRate[]>([]);

  const getAuthHeaders = useCallback(async () => {
    const t = token || await getIdToken();
    if (!t) return null;
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [token, getIdToken]);

  // Load products
  useEffect(() => {
    if (permLoading || !token) return;
    (async () => {
      try {
        const h = await getAuthHeaders();
        if (!h) { setLoading(false); return; }
        const res = await fetch(`${API_URL}/api/business-tools/analytics/products`, { headers: h });
        if (res.ok) {
          const data = await res.json();
          setProducts(data.products || []);
          if (data.products?.length > 0) setSelectedProduct(data.products[0].listingId);
        }
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [token, permLoading, getAuthHeaders]);

  // Load suppliers when product changes
  useEffect(() => {
    if (!selectedProduct || !token) return;
    (async () => {
      try {
        const h = await getAuthHeaders();
        if (!h) return;
        const res = await fetch(`${API_URL}/api/business-tools/analytics/suppliers?listing_id=${selectedProduct}`, { headers: h });
        if (res.ok) {
          const data = await res.json();
          setSuppliers(data.suppliers || []);
        }
      } catch { /* empty */ }
    })();
    setSelectedSupplier('');
  }, [selectedProduct, getAuthHeaders, token]);

  // Load chart data
  useEffect(() => {
    if (!selectedProduct || !token) return;
    if (period === 'custom' && (!customStart || !customEnd)) return;

    const loadCharts = async () => {
      setChartLoading(true);
      const h = await getAuthHeaders();
      if (!h) { setChartLoading(false); return; }
      const base = `${API_URL}/api/business-tools/analytics`;

      let dateParams = `period=${period}`;
      if (period === 'custom' && customStart && customEnd) {
        dateParams = `start_date=${customStart}T00:00:00Z&end_date=${customEnd}T23:59:59Z`;
      }

      const supParam = selectedSupplier ? `&supplier_id=${selectedSupplier}` : '';
      const q = `listing_id=${selectedProduct}&${dateParams}${supParam}`;

      const [summaryRes, priceRes, purchaseRes, stockRes, compRes] = await Promise.all([
        fetch(`${base}/summary?listing_id=${selectedProduct}`, { headers: h }),
        fetch(`${base}/price-trend?${q}`, { headers: h }),
        fetch(`${base}/purchase-trend?${q}`, { headers: h }),
        fetch(`${base}/stock-trend?listing_id=${selectedProduct}&${dateParams}`, { headers: h }),
        fetch(`${base}/supplier-comparison?listing_id=${selectedProduct}`, { headers: h }),
      ]);

      if (summaryRes.ok) setSummary(await summaryRes.json());
      if (priceRes.ok) setPriceTrend((await priceRes.json()).suppliers || []);
      if (purchaseRes.ok) setPurchaseTrend((await purchaseRes.json()).data || []);
      if (stockRes.ok) setStockTrend(await stockRes.json());
      if (compRes.ok) setSupplierComparison((await compRes.json()).suppliers || []);

      setChartLoading(false);
    };
    loadCharts();
  }, [selectedProduct, period, customStart, customEnd, selectedSupplier, getAuthHeaders, token]);

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  // Build unified price trend data for multi-line chart
  const pricePeriods = [...new Set(priceTrend.flatMap(s => s.data.map(d => d.period)))].sort();
  const priceChartData = pricePeriods.map(p => {
    const point: Record<string, string | number> = { period: p };
    priceTrend.forEach((s, i) => {
      const d = s.data.find(d => d.period === p);
      point[`supplier${i}`] = d ? d.avgRate : 0;
    });
    return point;
  });

  return (
    <div className="space-y-6" data-testid="analytics-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900" data-testid="analytics-heading">Product Analytics</h1>
        <p className="text-gray-600 mt-1">Analyze purchasing patterns, supplier prices, and inventory trends</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">Product</label>
            <select value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              data-testid="product-select">
              {products.map(p => (
                <option key={p.listingId} value={p.listingId}>
                  {p.productName}{p.sku ? ` (${p.sku})` : ''}
                </option>
              ))}
            </select>
          </div>
          {suppliers.length > 0 && (
            <div className="sm:w-48">
              <label className="block text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                <Filter className="h-3 w-3" /> Supplier
              </label>
              <select value={selectedSupplier} onChange={(e) => setSelectedSupplier(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                data-testid="supplier-filter">
                <option value="">All Suppliers</option>
                {suppliers.map(s => (
                  <option key={s.supplierId} value={s.supplierId}>{s.supplierName}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500">Period:</span>
          {PERIODS.map(pr => (
            <button key={pr.val} onClick={() => setPeriod(pr.val)} data-testid={`period-${pr.val}`}
              className={`px-3 py-1.5 text-sm rounded-lg transition ${period === pr.val ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {pr.label}
            </button>
          ))}
          {period === 'custom' && (
            <div className="flex items-center gap-2 ml-2">
              <input type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)}
                className="px-2 py-1 border border-gray-300 rounded text-sm" data-testid="custom-start" />
              <span className="text-gray-400">to</span>
              <input type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)}
                className="px-2 py-1 border border-gray-300 rounded text-sm" data-testid="custom-end" />
            </div>
          )}
        </div>
      </div>

      {chartLoading && <div className="flex items-center justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-blue-600" /></div>}

      {/* Summary Cards */}
      {summary && !chartLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4" data-testid="summary-cards">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><ShoppingCart className="h-3.5 w-3.5" /> Total POs</div>
            <p className="text-2xl font-bold text-gray-900">{summary.totalOrders}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Package2 className="h-3.5 w-3.5" /> Qty Ordered</div>
            <p className="text-2xl font-bold text-gray-900">{summary.totalQuantity.toLocaleString('en-IN')}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><IndianRupee className="h-3.5 w-3.5" /> Total Spend</div>
            <p className="text-2xl font-bold text-gray-900">₹{summary.totalSpend.toLocaleString('en-IN')}</p>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-1"><Layers className="h-3.5 w-3.5" /> Stock</div>
            <p className="text-2xl font-bold text-gray-900">{summary.currentStock}</p>
            {summary.minStock > 0 && <p className="text-xs text-orange-500 mt-0.5">Min: {summary.minStock}</p>}
          </div>
        </div>
      )}

      {!chartLoading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 1. Supplier Price Trend */}
          <div className="bg-white rounded-xl border p-5" data-testid="price-trend-chart">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Supplier Price Trend</h3>
            </div>
            {priceChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={priceChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {priceTrend.map((s, i) => (
                    <Line key={i} type="monotone" dataKey={`supplier${i}`} name={s.supplierName}
                      stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">No purchase data for this period</div>
            )}
          </div>

          {/* 2. Purchase Quantity Trend */}
          <div className="bg-white rounded-xl border p-5" data-testid="purchase-trend-chart">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-gray-900">Purchase Quantity Over Time</h3>
            </div>
            {purchaseTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={purchaseTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="quantity" fill="#16a34a" radius={[4, 4, 0, 0]} name="Quantity" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">No purchase data for this period</div>
            )}
          </div>

          {/* 3. Inventory Stock Trend */}
          <div className="bg-white rounded-xl border p-5" data-testid="stock-trend-chart">
            <div className="flex items-center gap-2 mb-4">
              <Package2 className="h-5 w-5 text-amber-600" />
              <h3 className="font-semibold text-gray-900">Inventory Stock Trend</h3>
            </div>
            {stockTrend.data.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={stockTrend.data.map(d => ({ ...d, date: new Date(d.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="bg-white shadow-lg border rounded-lg p-2 text-xs">
                        <p className="font-medium">{d.date}</p>
                        <p>Stock: <span className="font-semibold">{d.stock}</span></p>
                        <p className={d.change >= 0 ? 'text-green-600' : 'text-red-600'}>Change: {d.change > 0 ? '+' : ''}{d.change}</p>
                        <p className="text-gray-400">{d.type}</p>
                      </div>
                    );
                  }} />
                  {stockTrend.minStock > 0 && (
                    <ReferenceLine y={stockTrend.minStock} stroke="#f59e0b" strokeDasharray="5 5" label={{ value: `Min: ${stockTrend.minStock}`, fill: '#f59e0b', fontSize: 10 }} />
                  )}
                  <Line type="stepAfter" dataKey="stock" stroke="#d97706" strokeWidth={2} dot={{ r: 3, fill: '#d97706' }} name="Stock Level" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">No stock history for this period</div>
            )}
          </div>

          {/* 4. Supplier Rate Comparison */}
          <div className="bg-white rounded-xl border p-5" data-testid="supplier-comparison-chart">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">Supplier Rate Comparison</h3>
            </div>
            {supplierComparison.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={supplierComparison} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="supplierName" tick={{ fontSize: 11 }} width={120} />
                  <Tooltip formatter={(value) => [`₹${Number(value).toLocaleString('en-IN')}`, 'Rate']} />
                  <Bar dataKey="rate" radius={[0, 4, 4, 0]} name="Rate (₹)" fill="#7c3aed" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-gray-400 text-sm">No suppliers mapped to this product</div>
            )}
            {supplierComparison.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {supplierComparison.map(s => (
                  <span key={s.supplierId} className={`text-xs px-2 py-1 rounded-full ${s.isBestPrice ? 'bg-green-100 text-green-700 font-medium' : 'bg-gray-100 text-gray-600'}`}>
                    {s.supplierName}: ₹{s.rate.toLocaleString('en-IN')}{s.isBestPrice ? ' ★ Best' : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {products.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900">No Products Found</h3>
          <p className="text-sm text-gray-500 mt-1">Add products to your inventory to see analytics.</p>
        </div>
      )}
    </div>
  );
}
