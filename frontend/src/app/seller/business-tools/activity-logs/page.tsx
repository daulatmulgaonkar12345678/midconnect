"use client";

import { useState, useEffect, useCallback } from "react";
import { usePermissions } from "../layout";
import { Activity, Filter, Clock, User } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface ActivityLog {
  id: string;
  userId: string;
  userName: string;
  action: string;
  module: string;
  entityId?: string;
  details?: string;
  timestamp: string;
}

const ACTION_LABELS: Record<string, { label: string; color: string }> = {
  employee_created: { label: "Employee Created", color: "bg-blue-50 text-blue-700" },
  role_created: { label: "Role Created", color: "bg-purple-50 text-purple-700" },
  role_updated: { label: "Role Updated", color: "bg-purple-50 text-purple-700" },
  stock_adjusted: { label: "Stock Adjusted", color: "bg-amber-50 text-amber-700" },
  buyer_created: { label: "Buyer Added", color: "bg-green-50 text-green-700" },
  supplier_created: { label: "Supplier Added", color: "bg-teal-50 text-teal-700" },
  invoice_created: { label: "Invoice Created", color: "bg-indigo-50 text-indigo-700" },
  composite_product_created: { label: "Bundle Created", color: "bg-orange-50 text-orange-700" },
  composite_product_sold: { label: "Bundle Sold", color: "bg-emerald-50 text-emerald-700" }
};

const MODULE_OPTIONS = ["", "roles", "employees", "buyers", "suppliers", "inventory", "invoices", "composite_products"];

export default function ActivityLogsPage() {
  const { isAdmin, token } = usePermissions();
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [moduleFilter, setModuleFilter] = useState("");
  const [page, setPage] = useState(0);
  const limit = 30;

  const fetchLogs = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      let url = `${API_URL}/api/business-tools/activity-logs?limit=${limit}&skip=${page * limit}`;
      if (moduleFilter) url += `&module=${moduleFilter}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch { /* empty */ }
    setLoading(false);
  }, [token, moduleFilter, page]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  if (!isAdmin) {
    return <div className="p-6 text-center text-gray-500" data-testid="no-permission">Only admin users can view activity logs.</div>;
  }

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="space-y-6" data-testid="activity-logs-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Activity Logs</h1>
        <p className="text-sm text-gray-500 mt-1">Track team actions for audit purposes</p>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Filter className="w-4 h-4 text-gray-400" />
        <select value={moduleFilter} onChange={e => { setModuleFilter(e.target.value); setPage(0); }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm" data-testid="module-filter">
          <option value="">All Modules</option>
          {MODULE_OPTIONS.filter(Boolean).map(m => (
            <option key={m} value={m}>{m.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>
          ))}
        </select>
        <span className="text-sm text-gray-400">{total} total entries</span>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-100" data-testid="empty-state">
          <Activity className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No activity logs yet</p>
          <p className="text-sm text-gray-400 mt-1">Actions will be logged automatically as your team works</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map(log => {
            const actionInfo = ACTION_LABELS[log.action] || { label: log.action, color: "bg-gray-50 text-gray-700" };
            return (
              <div key={log.id} className="bg-white border border-gray-100 rounded-xl p-4 flex items-start gap-3" data-testid={`log-entry-${log.id}`}>
                <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-gray-900">{log.userName}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${actionInfo.color}`}>{actionInfo.label}</span>
                    <span className="text-xs text-gray-400 capitalize">{log.module?.replace(/_/g, " ")}</span>
                  </div>
                  {log.details && <p className="text-sm text-gray-600 mt-0.5">{log.details}</p>}
                  <div className="flex items-center gap-1 mt-1">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-400">{formatTime(log.timestamp)}</span>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Pagination */}
          {total > limit && (
            <div className="flex justify-center gap-2 pt-4">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40" data-testid="prev-page">Previous</button>
              <span className="text-sm text-gray-500 py-1.5">Page {page + 1} of {Math.ceil(total / limit)}</span>
              <button onClick={() => setPage(p => p + 1)} disabled={(page + 1) * limit >= total}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40" data-testid="next-page">Next</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
