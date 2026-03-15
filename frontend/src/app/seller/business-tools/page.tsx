'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { usePermissions } from './layout';
import Link from 'next/link';
import {
  Package2, Users, Truck, FileText, Layers, BarChart3,
  UserCog, Shield, Activity, Settings, IndianRupee,
  AlertTriangle, TrendingUp, Clock, Bell, ArrowRight,
  CheckCircle2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Metrics {
  totalRevenue: number;
  pendingPayments: number;
  overdueInvoices: number;
  thisMonthCollections: number;
  totalInvoices: number;
  alerts: { type: string; message: string; severity: string }[];
  unreadNotifications: number;
}

function fmt(n: number) { return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

export default function BusinessToolsPage() {
  const { getIdToken } = useAuth();
  const { hasPermission } = usePermissions();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const token = await getIdToken();
        const res = await fetch(`${API_URL}/api/business-tools/dashboard-metrics`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setMetrics(await res.json());
      } catch { /* empty */ }
      setMetricsLoading(false);
    })();
  }, [getIdToken]);

  const navItems = [
    { href: '/seller/business-tools/inventory', label: 'Inventory', desc: 'Manage stock and products', icon: Package2, color: 'emerald', perm: 'manage_inventory' },
    { href: '/seller/business-tools/buyers', label: 'Buyers', desc: 'Manage buyer contacts', icon: Users, color: 'blue', perm: 'manage_buyers' },
    { href: '/seller/business-tools/suppliers', label: 'Suppliers', desc: 'Track supplier details', icon: Truck, color: 'violet', perm: 'manage_buyers' },
    { href: '/seller/business-tools/invoices', label: 'Invoices', desc: 'Create and manage invoices', icon: FileText, color: 'indigo', perm: 'create_invoice' },
    { href: '/seller/business-tools/composite-products', label: 'Composite Products', desc: 'Build product bundles', icon: Layers, color: 'amber', perm: 'manage_inventory' },
    { href: '/seller/business-tools/reports', label: 'Reports', desc: 'View sales and profit reports', icon: BarChart3, color: 'cyan', perm: 'view_reports' },
    { href: '/seller/business-tools/notifications', label: 'Notifications', desc: 'Payment alerts and reminders', icon: Bell, color: 'rose', perm: 'create_invoice' },
    { href: '/seller/business-tools/settings', label: 'Business Settings', desc: 'Profile and invoice branding', icon: Settings, color: 'slate', perm: 'create_invoice' },
  ];

  const colorMap: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100',
    blue: 'bg-blue-50 text-blue-600 group-hover:bg-blue-100',
    violet: 'bg-violet-50 text-violet-600 group-hover:bg-violet-100',
    indigo: 'bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100',
    amber: 'bg-amber-50 text-amber-600 group-hover:bg-amber-100',
    cyan: 'bg-cyan-50 text-cyan-600 group-hover:bg-cyan-100',
    rose: 'bg-rose-50 text-rose-600 group-hover:bg-rose-100',
    slate: 'bg-slate-50 text-slate-600 group-hover:bg-slate-100',
  };

  return (
    <div className="space-y-6" data-testid="business-tools-home">
      {/* Dashboard Metrics */}
      {hasPermission('create_invoice') && (
        <div data-testid="dashboard-metrics">
          {metricsLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              {[1,2,3,4,5].map(i => <div key={i} className="bg-white rounded-xl border border-gray-100 p-4 animate-pulse h-24" />)}
            </div>
          ) : metrics ? (
            <>
              {/* Quick Alerts */}
              {metrics.alerts.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4" data-testid="quick-alerts">
                  {metrics.alerts.map((alert, i) => (
                    <div key={i} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                      alert.severity === 'high' ? 'bg-red-50 text-red-700 border border-red-100' :
                      alert.severity === 'medium' ? 'bg-amber-50 text-amber-700 border border-amber-100' :
                      'bg-emerald-50 text-emerald-700 border border-emerald-100'
                    }`} data-testid={`alert-${alert.type}`}>
                      {alert.severity === 'high' ? <AlertTriangle className="w-4 h-4" /> :
                       alert.severity === 'medium' ? <Clock className="w-4 h-4" /> :
                       <CheckCircle2 className="w-4 h-4" />}
                      {alert.message}
                    </div>
                  ))}
                </div>
              )}

              {/* Metric Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="metric-revenue">
                  <div className="flex items-center gap-2 text-emerald-500 mb-2">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Total Revenue</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 flex items-center gap-1">
                    <IndianRupee className="w-4 h-4" />{fmt(metrics.totalRevenue)}
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="metric-pending">
                  <div className="flex items-center gap-2 text-amber-500 mb-2">
                    <Clock className="w-4 h-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Pending</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 flex items-center gap-1">
                    <IndianRupee className="w-4 h-4" />{fmt(metrics.pendingPayments)}
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="metric-overdue">
                  <div className="flex items-center gap-2 text-red-500 mb-2">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Overdue</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900">{metrics.overdueInvoices}</p>
                </div>

                <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="metric-month">
                  <div className="flex items-center gap-2 text-indigo-500 mb-2">
                    <IndianRupee className="w-4 h-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">This Month</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900 flex items-center gap-1">
                    <IndianRupee className="w-4 h-4" />{fmt(metrics.thisMonthCollections)}
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-gray-100 p-4" data-testid="metric-invoices">
                  <div className="flex items-center gap-2 text-blue-500 mb-2">
                    <FileText className="w-4 h-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Invoices</span>
                  </div>
                  <p className="text-xl font-bold text-gray-900">{metrics.totalInvoices}</p>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Navigation Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="nav-grid">
        {navItems.filter(n => hasPermission(n.perm)).map(item => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}
              className="group flex items-center gap-3 p-4 bg-white rounded-xl border border-gray-100 hover:border-gray-200 hover:shadow-sm transition"
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorMap[item.color] || colorMap.slate}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-gray-800">{item.label}</p>
                  {item.label === 'Notifications' && metrics && metrics.unreadNotifications > 0 && (
                    <span className="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">{metrics.unreadNotifications}</span>
                  )}
                </div>
                <p className="text-xs text-gray-500">{item.desc}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
