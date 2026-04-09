'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  Search, Loader2, Users, Building2, Trash2, UserX, CheckCircle2,
  AlertCircle, ChevronLeft, ChevronRight, UserCheck, Shield
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface Employee {
  employeeId: string;
  name: string;
  email: string;
  phone: string;
  status: string;
  permissions: Record<string, unknown>;
  createdAt: string | null;
  sellerId: string | null;
  sellerEmail: string;
  companyName: string;
}

interface TopSeller {
  sellerId: string;
  companyName: string;
  email: string;
  employeeCount: number;
}

export default function AdminEmployeesPage() {
  const { getIdToken } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [topSellers, setTopSellers] = useState<TopSeller[]>([]);
  const [stats, setStats] = useState({ totalEmployees: 0, activeEmployees: 0, totalSellersWithEmployees: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);

  const showToast = (type: 'success' | 'error', msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getIdToken();
      const params = new URLSearchParams({ page: String(page), limit: '25' });
      if (search) params.set('search', search);
      const res = await fetch(`${API_URL}/api/admin/employees?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setEmployees(data.employees || []);
        setTotalPages(data.pages || 1);
        setStats(data.stats || { totalEmployees: 0, activeEmployees: 0, totalSellersWithEmployees: 0 });
        setTopSellers(data.topSellers || []);
      }
    } catch { /* silent */ }
    setLoading(false);
  }, [getIdToken, page, search]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDelete = async (employeeId: string, employeeName: string) => {
    if (!confirm(`Remove employee "${employeeName}"? They will lose access to their company account.`)) return;
    setDeletingId(employeeId);
    try {
      const token = await getIdToken();
      const res = await fetch(`${API_URL}/api/admin/employees/${employeeId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast('success', `Employee "${employeeName}" removed`);
        fetchData();
      } else {
        const err = await res.json();
        showToast('error', err.detail || 'Failed to remove employee');
      }
    } catch {
      showToast('error', 'Network error');
    }
    setDeletingId(null);
  };

  return (
    <div className="max-w-7xl mx-auto" data-testid="admin-employees-page">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl shadow-lg text-sm font-medium animate-in slide-in-from-right-5 ${
          toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`} data-testid="toast-notification">
          {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900" data-testid="page-title">Employee Management</h1>
        <p className="text-sm text-gray-500 mt-1">View and manage employees across all seller businesses</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="flex items-center gap-3 p-4 rounded-xl bg-blue-50 border border-blue-100">
          <Users className="h-6 w-6 text-blue-600" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{stats.totalEmployees}</div>
            <div className="text-xs text-gray-500">Total Employees</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-100">
          <UserCheck className="h-6 w-6 text-emerald-600" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{stats.activeEmployees}</div>
            <div className="text-xs text-gray-500">Active</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-4 rounded-xl bg-violet-50 border border-violet-100">
          <Building2 className="h-6 w-6 text-violet-600" />
          <div>
            <div className="text-2xl font-bold text-gray-900">{stats.totalSellersWithEmployees}</div>
            <div className="text-xs text-gray-500">Businesses with Team</div>
          </div>
        </div>
      </div>

      {/* Top Sellers by Employee Count */}
      {topSellers.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Businesses by Team Size</h3>
          <div className="flex flex-wrap gap-2">
            {topSellers.slice(0, 10).map(s => (
              <button
                key={s.sellerId}
                onClick={() => { setSearch(s.companyName || s.email); setPage(1); }}
                className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm hover:bg-gray-50 transition"
                data-testid={`seller-chip-${s.sellerId}`}
              >
                <Building2 className="h-3.5 w-3.5 text-gray-400" />
                <span className="font-medium text-gray-700 truncate max-w-[150px]">{s.companyName || s.email}</span>
                <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-semibold">{s.employeeCount}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by employee name, email, or company..."
            className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-300 focus:border-blue-300 outline-none"
            data-testid="search-input"
          />
        </div>
        {search && (
          <button onClick={() => { setSearch(''); setPage(1); }} className="text-sm text-gray-500 hover:text-gray-700">
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
        </div>
      ) : employees.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Users className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="text-sm">{search ? 'No employees match your search' : 'No employees found'}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="employees-table">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Employee</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Company</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Permissions</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Joined</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {employees.map((emp) => {
                  const permKeys = Object.entries(emp.permissions || {})
                    .filter(([, v]) => v === true || v === 'full')
                    .map(([k]) => k);

                  return (
                    <tr key={emp.employeeId} className="group hover:bg-gray-50/50" data-testid={`employee-row-${emp.employeeId}`}>
                      <td className="px-4 py-3">
                        <div>
                          <div className="font-medium text-gray-900">{emp.name || 'Unnamed'}</div>
                          <div className="text-xs text-gray-400">{emp.email}</div>
                          {emp.phone && <div className="text-xs text-gray-400">{emp.phone}</div>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-gray-300" />
                          <div>
                            <div className="font-medium text-gray-700 truncate max-w-[180px]">{emp.companyName || 'Unknown'}</div>
                            <div className="text-xs text-gray-400 truncate max-w-[180px]">{emp.sellerEmail}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                          emp.status === 'active'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-red-50 text-red-600 border-red-200'
                        }`}>
                          {emp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {permKeys.length > 0 ? permKeys.slice(0, 4).map(p => (
                            <span key={p} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-[10px] rounded font-medium">
                              {p}
                            </span>
                          )) : (
                            <span className="text-[10px] text-gray-400">None</span>
                          )}
                          {permKeys.length > 4 && (
                            <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 text-[10px] rounded">+{permKeys.length - 4}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {emp.createdAt ? new Date(emp.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '-'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleDelete(emp.employeeId, emp.name || emp.email)}
                          disabled={deletingId === emp.employeeId}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition disabled:opacity-50"
                          data-testid={`delete-employee-${emp.employeeId}`}
                        >
                          {deletingId === emp.employeeId ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                          Remove
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6" data-testid="pagination">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
