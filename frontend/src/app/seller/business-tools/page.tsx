'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from './layout';
import { useNetworkContext } from '@/context/NetworkContext';
import Link from 'next/link';
import {
  Package2, Truck, FileText, Layers, BarChart3,
  IndianRupee, AlertTriangle, TrendingUp, Clock,
  ArrowRight, ShoppingCart, LineChart as LineChartIcon, Loader2,
  ArrowUpRight, ArrowDownRight, PackageX, Zap, CloudOff, RefreshCw
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

const PIE_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#65a30d'];

interface HomeCharts {
  salesTrend: Array<{ date: string; amount: number; orders: number }>;
  purchaseTrend: Array<{ date: string; amount: number; orders: number }>;
  topProducts: Array<{ name: string; quantity: number; revenue: number }>;
  stockDistribution: Array<{ category: string; stock: number; products: number }>;
}

interface OverviewData {
  totalOutstanding: number;
  outstandingCount: number;
  overdueInvoices: number;
  lowStockCount: number;
  topProduct: { name: string | null; qtySold: number; revenue: number };
  monthlySales: number;
  monthlyInvoiceCount: number;
  growthPercentage: number;
}

function fmtCurrency(n: number) { return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function BusinessToolsHomePage() {
  const { getIdToken } = useAuth();
  const { hasPermission, token, loading: permLoading } = usePermissions();
  const [charts, setCharts] = useState<HomeCharts | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (permLoading || !token) return;
    (async () => {
      try {
        const h = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
        const [chartRes, ovRes] = await Promise.all([
          fetch(`${API_URL}/api/business-tools/home/charts`, { headers: h }),
          fetch(`${API_URL}/api/business-tools/reports/overview`, { headers: h }),
        ]);
        if (chartRes.ok) setCharts(await chartRes.json());
        if (ovRes.ok) setOverview(await ovRes.json());
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [token, permLoading]);

  const quickLinks = [
    { href: '/seller/business-tools/inventory', label: 'Inventory', desc: 'Manage stock and products', icon: Package2, color: 'bg-blue-50 text-blue-600' },
    { href: '/seller/business-tools/invoices', label: 'Invoices', desc: 'Create and manage invoices', icon: FileText, color: 'bg-indigo-50 text-indigo-600' },
    { href: '/seller/business-tools/charts', label: 'Charts & Graphs', desc: 'Detailed analytics', icon: LineChartIcon, color: 'bg-cyan-50 text-cyan-600' },
    { href: '/seller/business-tools/suppliers', label: 'Suppliers', desc: 'Track supplier details', icon: Truck, color: 'bg-violet-50 text-violet-600' },
    { href: '/seller/business-tools/purchase-orders', label: 'Purchase Orders', desc: 'Track purchasing', icon: ShoppingCart, color: 'bg-green-50 text-green-600' },
    { href: '/seller/business-tools/reports', label: 'Reports', desc: 'View sales reports', icon: BarChart3, color: 'bg-amber-50 text-amber-600' },
  ];

  const { isOnline, syncState, triggerSync } = useNetworkContext();

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  return (
    <div className="space-y-6" data-testid="business-tools-home">
      <div>
        <h1 className="text-2xl font-bold text-gray-900" data-testid="home-heading">Business Dashboard</h1>
        <p className="text-gray-600 mt-1">Overview of your business operations</p>
      </div>

      {/* Sync Status Widget */}
      {(syncState.pendingCount > 0 || !isOnline) && (
        <div className={`rounded-xl border p-4 flex items-center justify-between ${isOnline ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`} data-testid="sync-status-widget">
          <div className="flex items-center gap-3">
            <CloudOff className={`w-5 h-5 ${isOnline ? 'text-amber-600' : 'text-red-600'}`} />
            <div>
              <p className={`text-sm font-medium ${isOnline ? 'text-amber-800' : 'text-red-800'}`}>
                {!isOnline ? 'You are offline' : `${syncState.pendingCount} item${syncState.pendingCount > 1 ? 's' : ''} pending sync`}
              </p>
              {syncState.lastSyncTime && (
                <p className="text-xs text-gray-500">Last synced: {syncState.lastSyncTime.toLocaleTimeString('en-IN')}</p>
              )}
            </div>
          </div>
          {isOnline && syncState.pendingCount > 0 && (
            <button onClick={triggerSync} className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700" data-testid="dashboard-sync-btn">
              <RefreshCw className={`w-3.5 h-3.5 ${syncState.isSyncing ? 'animate-spin' : ''}`} />
              {syncState.isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
          )}
        </div>
      )}

      {/* Business Insights */}
      {overview && (
        <div data-testid="business-insights">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Business Insights</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">

            {/* Outstanding Alerts */}
            <Link href="/seller/business-tools/reports?tab=outstanding"
              className="group bg-white rounded-xl border border-gray-100 hover:border-red-200 hover:shadow-md transition-all p-4 space-y-2"
              data-testid="insight-outstanding">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${overview.totalOutstanding > 0 ? "bg-red-50" : "bg-green-50"}`}>
                    <Clock className={`w-4 h-4 ${overview.totalOutstanding > 0 ? "text-red-500" : "text-green-500"}`} />
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Outstanding</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-red-400 transition-colors" />
              </div>
              <p className="text-lg font-bold text-gray-900 flex items-center gap-0.5">
                <IndianRupee className="w-4 h-4" />{fmtCurrency(overview.totalOutstanding)}
              </p>
              <div className="flex items-center gap-3 text-[11px]">
                <span className="text-gray-500">{overview.outstandingCount} pending</span>
                {overview.overdueInvoices > 0 && (
                  <span className="text-red-600 font-semibold">{overview.overdueInvoices} overdue 90+d</span>
                )}
              </div>
            </Link>

            {/* Low Stock Alerts */}
            <Link href="/seller/business-tools/reports?tab=low-stock"
              className="group bg-white rounded-xl border border-gray-100 hover:border-amber-200 hover:shadow-md transition-all p-4 space-y-2"
              data-testid="insight-low-stock">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${overview.lowStockCount > 0 ? "bg-amber-50" : "bg-green-50"}`}>
                    <PackageX className={`w-4 h-4 ${overview.lowStockCount > 0 ? "text-amber-500" : "text-green-500"}`} />
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Low Stock</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-amber-400 transition-colors" />
              </div>
              <p className={`text-2xl font-bold ${overview.lowStockCount > 0 ? "text-amber-600" : "text-green-600"}`}>
                {overview.lowStockCount}
              </p>
              <p className="text-[11px] text-gray-500">
                {overview.lowStockCount > 0 ? "products below minimum" : "All stock levels healthy"}
              </p>
            </Link>

            {/* Top Product */}
            <Link href="/seller/business-tools/reports?tab=product-perf"
              className="group bg-white rounded-xl border border-gray-100 hover:border-indigo-200 hover:shadow-md transition-all p-4 space-y-2"
              data-testid="insight-top-product">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-50">
                    <Zap className="w-4 h-4 text-indigo-500" />
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Top Product</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-indigo-400 transition-colors" />
              </div>
              {overview.topProduct?.name ? (
                <>
                  <p className="text-sm font-bold text-gray-900 truncate">{overview.topProduct.name}</p>
                  <div className="flex items-center gap-3 text-[11px]">
                    <span className="text-gray-500">{overview.topProduct.qtySold} sold</span>
                    <span className="text-indigo-600 font-semibold flex items-center"><IndianRupee className="w-3 h-3" />{fmtCurrency(overview.topProduct.revenue)}</span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-gray-400">No sales this month</p>
              )}
            </Link>

            {/* Monthly Sales */}
            <Link href="/seller/business-tools/reports?tab=sales"
              className="group bg-white rounded-xl border border-gray-100 hover:border-green-200 hover:shadow-md transition-all p-4 space-y-2"
              data-testid="insight-monthly-sales">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-green-50">
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">This Month</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-green-400 transition-colors" />
              </div>
              <p className="text-lg font-bold text-gray-900 flex items-center gap-0.5">
                <IndianRupee className="w-4 h-4" />{fmtCurrency(overview.monthlySales)}
              </p>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-gray-500">{overview.monthlyInvoiceCount} invoices</span>
                {overview.growthPercentage !== 0 && (
                  <span className={`font-semibold flex items-center gap-0.5 ${overview.growthPercentage > 0 ? "text-green-600" : "text-red-600"}`}>
                    {overview.growthPercentage > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {Math.abs(overview.growthPercentage)}% vs last month
                  </span>
                )}
              </div>
            </Link>

          </div>
        </div>
      )}

      {/* Quick Charts */}
      {charts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" data-testid="home-charts">
          {/* Sales Trend */}
          <div className="bg-white rounded-xl border p-5" data-testid="home-sales-trend">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Sales Trend (Last 30 Days)</h3>
            </div>
            {charts.salesTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={charts.salesTrend.map(d => ({ ...d, date: d.date.slice(5) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [`₹${Number(value).toLocaleString('en-IN')}`, 'Sales']} />
                  <Line type="monotone" dataKey="amount" stroke="#2563eb" strokeWidth={2} dot={false} name="Sales" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">No sales data yet</div>
            )}
          </div>

          {/* Purchase Trend */}
          <div className="bg-white rounded-xl border p-5" data-testid="home-purchase-trend">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingCart className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-gray-900">Purchase Trend (Last 30 Days)</h3>
            </div>
            {charts.purchaseTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.purchaseTrend.map(d => ({ ...d, date: d.date.slice(5) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(value) => [`₹${Number(value).toLocaleString('en-IN')}`, 'Purchases']} />
                  <Bar dataKey="amount" fill="#16a34a" radius={[4, 4, 0, 0]} name="Purchases" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">No purchase data yet</div>
            )}
          </div>

          {/* Top Selling Products */}
          <div className="bg-white rounded-xl border p-5" data-testid="home-top-products">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-5 w-5 text-amber-600" />
              <h3 className="font-semibold text-gray-900">Top Selling Products</h3>
            </div>
            {charts.topProducts.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={charts.topProducts.slice(0, 6)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={100} />
                  <Tooltip formatter={(value) => [Number(value).toLocaleString('en-IN'), 'Qty Sold']} />
                  <Bar dataKey="quantity" fill="#d97706" radius={[0, 4, 4, 0]} name="Quantity" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">No sales data yet</div>
            )}
          </div>

          {/* Stock Distribution by Category */}
          <div className="bg-white rounded-xl border p-5" data-testid="home-stock-distribution">
            <div className="flex items-center gap-2 mb-4">
              <Layers className="h-5 w-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">Stock Distribution by Category</h3>
            </div>
            {charts.stockDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={charts.stockDistribution}
                    dataKey="stock"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {charts.stockDistribution.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [Number(value).toLocaleString('en-IN'), 'Stock']} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[220px] text-gray-400 text-sm">No stock data yet</div>
            )}
          </div>
        </div>
      )}

      {/* Quick Links */}
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="nav-grid">
          {quickLinks.filter(n => hasPermission('create_invoice') || hasPermission('manage_inventory')).map(item => {
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href}
                className="group flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition"
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}>
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${item.color}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-800">{item.label}</p>
                  <p className="text-xs text-gray-500">{item.desc}</p>
                </div>
                <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
