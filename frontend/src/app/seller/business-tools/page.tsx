'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from './layout';
import Link from 'next/link';
import {
  Package2, Users, Truck, FileText, Layers, BarChart3,
  Settings, IndianRupee, AlertTriangle, TrendingUp, Clock,
  Bell, ArrowRight, CheckCircle2, ShoppingCart, LineChart as LineChartIcon, Loader2
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const PIE_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2', '#db2777', '#65a30d'];

interface HomeSummary {
  totalProducts: number;
  lowStockItems: number;
  pendingPOs: number;
  totalSuppliers: number;
  todaySales: number;
  todaySalesCount: number;
  totalRevenue: number;
}

interface HomeCharts {
  salesTrend: Array<{ date: string; amount: number; orders: number }>;
  purchaseTrend: Array<{ date: string; amount: number; orders: number }>;
  topProducts: Array<{ name: string; quantity: number; revenue: number }>;
  stockDistribution: Array<{ category: string; stock: number; products: number }>;
}

function fmt(n: number) { return n.toLocaleString('en-IN', { maximumFractionDigits: 0 }); }
function fmtCurrency(n: number) { return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function BusinessToolsHomePage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [summary, setSummary] = useState<HomeSummary | null>(null);
  const [charts, setCharts] = useState<HomeCharts | null>(null);
  const [loading, setLoading] = useState(true);

  const authHeaders = useCallback(async () => {
    const t = await getIdToken();
    return { Authorization: `Bearer ${t}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  useEffect(() => {
    (async () => {
      try {
        const h = await authHeaders();
        const [sumRes, chartRes] = await Promise.all([
          fetch(`${API_URL}/api/business-tools/home/summary`, { headers: h }),
          fetch(`${API_URL}/api/business-tools/home/charts`, { headers: h }),
        ]);
        if (sumRes.ok) setSummary(await sumRes.json());
        if (chartRes.ok) setCharts(await chartRes.json());
      } catch { /* empty */ }
      setLoading(false);
    })();
  }, [authHeaders]);

  const quickLinks = [
    { href: '/seller/business-tools/inventory', label: 'Inventory', desc: 'Manage stock and products', icon: Package2, color: 'bg-blue-50 text-blue-600' },
    { href: '/seller/business-tools/invoices', label: 'Invoices', desc: 'Create and manage invoices', icon: FileText, color: 'bg-indigo-50 text-indigo-600' },
    { href: '/seller/business-tools/charts', label: 'Charts & Graphs', desc: 'Detailed analytics', icon: LineChartIcon, color: 'bg-cyan-50 text-cyan-600' },
    { href: '/seller/business-tools/suppliers', label: 'Suppliers', desc: 'Track supplier details', icon: Truck, color: 'bg-violet-50 text-violet-600' },
    { href: '/seller/business-tools/purchase-orders', label: 'Purchase Orders', desc: 'Track purchasing', icon: ShoppingCart, color: 'bg-green-50 text-green-600' },
    { href: '/seller/business-tools/reports', label: 'Reports', desc: 'View sales reports', icon: BarChart3, color: 'bg-amber-50 text-amber-600' },
  ];

  if (loading) return <div className="flex items-center justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;

  return (
    <div className="space-y-6" data-testid="business-tools-home">
      <div>
        <h1 className="text-2xl font-bold text-gray-900" data-testid="home-heading">Business Dashboard</h1>
        <p className="text-gray-600 mt-1">Overview of your business operations</p>
      </div>

      {/* Summary Widgets */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="home-summary-widgets">
          <div className="bg-white rounded-xl border p-4" data-testid="widget-total-products">
            <div className="flex items-center gap-2 text-blue-500 mb-2">
              <Package2 className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Products</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{fmt(summary.totalProducts)}</p>
          </div>
          <div className="bg-white rounded-xl border p-4" data-testid="widget-low-stock">
            <div className="flex items-center gap-2 text-red-500 mb-2">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Low Stock</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{fmt(summary.lowStockItems)}</p>
          </div>
          <div className="bg-white rounded-xl border p-4" data-testid="widget-pending-pos">
            <div className="flex items-center gap-2 text-amber-500 mb-2">
              <Clock className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Pending POs</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{fmt(summary.pendingPOs)}</p>
          </div>
          <div className="bg-white rounded-xl border p-4" data-testid="widget-suppliers">
            <div className="flex items-center gap-2 text-purple-500 mb-2">
              <Truck className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Suppliers</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{fmt(summary.totalSuppliers)}</p>
          </div>
          <div className="bg-white rounded-xl border p-4" data-testid="widget-today-sales">
            <div className="flex items-center gap-2 text-green-500 mb-2">
              <TrendingUp className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Today Sales</span>
            </div>
            <p className="text-xl font-bold text-gray-900 flex items-center">
              <IndianRupee className="w-3.5 h-3.5" />{fmtCurrency(summary.todaySales)}
            </p>
          </div>
          <div className="bg-white rounded-xl border p-4" data-testid="widget-total-revenue">
            <div className="flex items-center gap-2 text-emerald-500 mb-2">
              <IndianRupee className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Revenue</span>
            </div>
            <p className="text-xl font-bold text-gray-900 flex items-center">
              <IndianRupee className="w-3.5 h-3.5" />{fmtCurrency(summary.totalRevenue)}
            </p>
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
