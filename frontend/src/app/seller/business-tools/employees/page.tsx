'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import {
  Users, Search, UserPlus, UserMinus, Shield, Loader2,
  Mail, Phone, Clock, AlertTriangle, CheckCircle, XCircle, Settings, Eye, Pencil, History
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const PERMISSION_MODULES = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'inventory', label: 'Inventory' },
  { key: 'invoices', label: 'Invoices' },
  { key: 'quotations', label: 'Quotations' },
  { key: 'purchase_orders', label: 'Purchase Orders' },
  { key: 'reports', label: 'Reports' },
  { key: 'buyers', label: 'Buyers' },
  { key: 'suppliers', label: 'Suppliers' },
  { key: 'employees', label: 'Employees' },
  { key: 'settings', label: 'Settings' },
];

interface ModPerm { view: boolean; action: boolean; }
interface Employee {
  id: string; email: string; name: string; phone: string;
  role: string; status: string; permissions: Record<string, ModPerm>;
  linkedAt: string; unlinkedAt: string; createdAt: string;
}

type Tab = 'active' | 'pending' | 'unlinked';

export default function EmployeeManagementPage() {
  const { getIdToken } = useAuth();
  const [tab, setTab] = useState<Tab>('active');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleTemplates, setRoleTemplates] = useState<Record<string, Record<string, ModPerm>>>({});

  // Search
  const [searchEmail, setSearchEmail] = useState('');
  const [searchResult, setSearchResult] = useState<Record<string, unknown> | null>(null);
  const [searching, setSearching] = useState(false);

  // Link modal
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkTarget, setLinkTarget] = useState<{ id: string; email: string; name: string } | null>(null);
  const [linkRole, setLinkRole] = useState('');
  const [linkPerms, setLinkPerms] = useState<Record<string, ModPerm>>({});
  const [linking, setLinking] = useState(false);

  // Edit modal
  const [editEmployee, setEditEmployee] = useState<Employee | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editPerms, setEditPerms] = useState<Record<string, ModPerm>>({});
  const [editStatus, setEditStatus] = useState('');
  const [saving, setSaving] = useState(false);

  // Logs
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<Record<string, unknown>[]>([]);

  const authHeaders = useCallback(async () => {
    const token = await getIdToken();
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchEmployees = useCallback(async () => {
    setLoading(true);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/list?tab=${tab}`, { headers: h });
      if (res.ok) { const data = await res.json(); setEmployees(data.employees || []); }
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders, tab]);

  const fetchTemplates = useCallback(async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/role-templates`, { headers: h });
      if (res.ok) { const data = await res.json(); setRoleTemplates(data.templates || {}); }
    } catch { /* empty */ }
  }, [authHeaders]);

  useEffect(() => { fetchEmployees(); }, [fetchEmployees]);
  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  // Initialize permissions for all modules
  const initPerms = (): Record<string, ModPerm> => {
    const p: Record<string, ModPerm> = {};
    PERMISSION_MODULES.forEach(m => { p[m.key] = { view: false, action: false }; });
    return p;
  };

  // Search by email
  const handleSearch = async () => {
    if (!searchEmail.trim()) { toast.error('Enter an email'); return; }
    setSearching(true);
    setSearchResult(null);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/search?email=${encodeURIComponent(searchEmail.trim())}`, { headers: h });
      const data = await res.json();
      setSearchResult(data);
    } catch { toast.error('Search failed'); }
    setSearching(false);
  };

  // Open link modal
  const openLinkModal = (user: Record<string, unknown>) => {
    setLinkTarget({ id: user.id as string, email: user.email as string, name: user.name as string });
    setLinkRole('');
    setLinkPerms(initPerms());
    setShowLinkModal(true);
  };

  // Apply role template
  const applyTemplate = (templateName: string, setter: (p: Record<string, ModPerm>) => void, roleSetter: (r: string) => void) => {
    const tpl = roleTemplates[templateName];
    if (tpl) {
      const perms: Record<string, ModPerm> = {};
      PERMISSION_MODULES.forEach(m => {
        perms[m.key] = tpl[m.key] || { view: false, action: false };
      });
      setter(perms);
      roleSetter(templateName);
    }
  };

  // Link employee
  const handleLink = async () => {
    if (!linkTarget || !linkRole) { toast.error('Select a role'); return; }
    setLinking(true);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/link`, {
        method: 'POST', headers: h,
        body: JSON.stringify({ email: linkTarget.email, role: linkRole, permissions: linkPerms }),
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); setLinking(false); return; }
      toast.success(data.message);
      setShowLinkModal(false);
      setSearchResult(null);
      setSearchEmail('');
      fetchEmployees();
    } catch { toast.error('Link failed'); }
    setLinking(false);
  };

  // Unlink
  const handleUnlink = async (id: string) => {
    if (!confirm('Unlink this employee? Their access will be revoked immediately.')) return;
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/${id}/unlink`, { method: 'POST', headers: h });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); return; }
      toast.success(data.message);
      fetchEmployees();
    } catch { toast.error('Unlink failed'); }
  };

  // Open edit
  const openEdit = (emp: Employee) => {
    setEditEmployee(emp);
    setEditRole(emp.role);
    setEditStatus(emp.status);
    const perms: Record<string, ModPerm> = {};
    PERMISSION_MODULES.forEach(m => {
      perms[m.key] = emp.permissions[m.key] || { view: false, action: false };
    });
    setEditPerms(perms);
  };

  // Save edit
  const handleSaveEdit = async () => {
    if (!editEmployee) return;
    setSaving(true);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/${editEmployee.id}`, {
        method: 'PUT', headers: h,
        body: JSON.stringify({ role: editRole, permissions: editPerms, status: editStatus }),
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); setSaving(false); return; }
      toast.success('Access updated');
      setEditEmployee(null);
      fetchEmployees();
    } catch { toast.error('Update failed'); }
    setSaving(false);
  };

  // Re-link
  const handleRelink = (emp: Employee) => {
    setLinkTarget({ id: emp.id, email: emp.email, name: emp.name });
    setLinkRole('');
    setLinkPerms(initPerms());
    setShowLinkModal(true);
  };

  // Fetch logs
  const fetchLogs = async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/logs`, { headers: h });
      if (res.ok) { const data = await res.json(); setLogs(data.logs || []); }
    } catch { /* empty */ }
    setShowLogs(true);
  };

  const statusBadge = (status: string) => {
    if (status === 'active') return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium" data-testid="status-active">Active</span>;
    if (status === 'disabled') return <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium" data-testid="status-disabled">Disabled</span>;
    if (status === 'unlinked') return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium" data-testid="status-unlinked">Unlinked</span>;
    return <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium" data-testid="status-pending">Pending</span>;
  };

  // Permission grid component
  const PermissionGrid = ({ perms, onChange, disabled }: { perms: Record<string, ModPerm>; onChange: (p: Record<string, ModPerm>) => void; disabled?: boolean }) => (
    <div className="space-y-1" data-testid="permission-grid">
      <div className="grid grid-cols-12 gap-2 text-xs text-gray-500 font-medium pb-1 border-b">
        <div className="col-span-4">Module</div>
        <div className="col-span-4 text-center flex items-center justify-center gap-1"><Eye className="w-3 h-3" /> View</div>
        <div className="col-span-4 text-center flex items-center justify-center gap-1"><Pencil className="w-3 h-3" /> Action</div>
      </div>
      {PERMISSION_MODULES.map(m => (
        <div key={m.key} className="grid grid-cols-12 gap-2 items-center py-1.5 hover:bg-gray-50 rounded" data-testid={`perm-row-${m.key}`}>
          <div className="col-span-4 text-sm text-gray-700">{m.label}</div>
          <div className="col-span-4 flex justify-center">
            <input type="checkbox" checked={perms[m.key]?.view || false} disabled={disabled}
              onChange={e => {
                const np = { ...perms };
                np[m.key] = { ...np[m.key], view: e.target.checked };
                if (!e.target.checked) np[m.key].action = false;
                onChange(np);
              }}
              className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
              data-testid={`perm-view-${m.key}`}
            />
          </div>
          <div className="col-span-4 flex justify-center">
            <input type="checkbox" checked={perms[m.key]?.action || false} disabled={disabled || !perms[m.key]?.view}
              onChange={e => {
                const np = { ...perms };
                np[m.key] = { ...np[m.key], action: e.target.checked };
                onChange(np);
              }}
              className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 disabled:opacity-30"
              data-testid={`perm-action-${m.key}`}
            />
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-4" data-testid="employee-mgmt-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900" data-testid="employee-heading">Employee Management</h2>
          <p className="text-sm text-gray-500">Link, manage, and control employee access in real-time</p>
        </div>
        <button onClick={fetchLogs} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200" data-testid="view-logs-btn">
          <History className="w-3.5 h-3.5" /> Audit Logs
        </button>
      </div>

      {/* Search + Link Section */}
      <div className="bg-white rounded-xl border p-4 space-y-3" data-testid="search-section">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2"><UserPlus className="w-4 h-4 text-indigo-600" /> Link New Employee</h3>
        <p className="text-xs text-gray-500">Search by the employee&apos;s registered email. They must have a buyer account first. If not found, ask them to register at the platform.</p>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="email" value={searchEmail} onChange={e => setSearchEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="Enter employee email..." className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm" data-testid="search-email-input" />
          </div>
          <button onClick={handleSearch} disabled={searching} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5" data-testid="search-btn">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Search
          </button>
        </div>

        {/* Search Result */}
        {searchResult && (
          <div className="mt-2 p-3 rounded-lg border bg-gray-50" data-testid="search-result">
            {!searchResult.found && (
              <div className="flex items-center gap-2 text-sm text-amber-700">
                <AlertTriangle className="w-4 h-4" />
                <span>{searchResult.message as string}</span>
              </div>
            )}
            {searchResult.found && searchResult.alreadyLinked && (
              <div className="flex items-center gap-2 text-sm text-blue-700">
                <CheckCircle className="w-4 h-4" />
                <span>{searchResult.message as string}</span>
              </div>
            )}
            {searchResult.found && searchResult.linkedElsewhere && (
              <div className="flex items-center gap-2 text-sm text-red-700">
                <XCircle className="w-4 h-4" />
                <span>{searchResult.message as string}</span>
              </div>
            )}
            {searchResult.found && searchResult.canLink && (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">{(searchResult.user as Record<string, unknown>)?.name as string || 'No name'}</p>
                  <p className="text-xs text-gray-500">{(searchResult.user as Record<string, unknown>)?.email as string} {(searchResult.user as Record<string, unknown>)?.phone ? `| ${(searchResult.user as Record<string, unknown>)?.phone}` : ''}</p>
                </div>
                <button onClick={() => openLinkModal(searchResult.user as Record<string, unknown>)} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 flex items-center gap-1" data-testid="link-employee-btn">
                  <UserPlus className="w-3.5 h-3.5" /> Link Employee
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1" data-testid="employee-tabs">
        {([['active', 'Active', CheckCircle], ['pending', 'Pending', Clock], ['unlinked', 'Unlinked', UserMinus]] as [Tab, string, typeof Users][]).map(([key, label, Icon]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-colors ${tab === key ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
            data-testid={`tab-${key}`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>

      {/* Employee List */}
      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="w-8 h-8 animate-spin text-indigo-600" /></div>
      ) : employees.length === 0 ? (
        <div className="text-center py-10 bg-white rounded-xl border" data-testid="empty-employees">
          <Users className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-gray-500 text-sm">
            {tab === 'active' ? 'No active employees. Search and link one above.' : tab === 'pending' ? 'No pending users found.' : 'No unlinked employees.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2" data-testid="employee-list">
          {employees.map(emp => (
            <div key={emp.id} className="bg-white rounded-xl border p-4" data-testid={`employee-${emp.id}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold text-sm">
                    {(emp.name || emp.email || '?')[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 text-sm" data-testid={`emp-name-${emp.id}`}>{emp.name || 'No Name'}</span>
                      {statusBadge(emp.status)}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500 mt-0.5">
                      <span className="flex items-center gap-1"><Mail className="w-3 h-3" /> {emp.email}</span>
                      {emp.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {emp.phone}</span>}
                    </div>
                    {emp.role && emp.role !== 'unassigned' && (
                      <span className="text-xs text-indigo-600 font-medium flex items-center gap-1 mt-0.5">
                        <Shield className="w-3 h-3" /> {emp.role}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {tab === 'active' && (
                    <>
                      <button onClick={() => openEdit(emp)} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200 flex items-center gap-1" data-testid={`edit-access-${emp.id}`}>
                        <Settings className="w-3.5 h-3.5" /> Edit Access
                      </button>
                      <button onClick={() => handleUnlink(emp.id)} className="px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium flex items-center gap-1" data-testid={`unlink-${emp.id}`}>
                        <UserMinus className="w-3.5 h-3.5" /> Unlink
                      </button>
                    </>
                  )}
                  {tab === 'pending' && (
                    <button onClick={() => openLinkModal({ id: emp.id, email: emp.email, name: emp.name } as Record<string, unknown>)} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 flex items-center gap-1" data-testid={`link-pending-${emp.id}`}>
                      <UserPlus className="w-3.5 h-3.5" /> Link
                    </button>
                  )}
                  {tab === 'unlinked' && (
                    <button onClick={() => handleRelink(emp)} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 flex items-center gap-1" data-testid={`relink-${emp.id}`}>
                      <UserPlus className="w-3.5 h-3.5" /> Re-link
                    </button>
                  )}
                </div>
              </div>

              {/* Permission summary for active */}
              {tab === 'active' && emp.permissions && Object.keys(emp.permissions).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 pt-2 border-t">
                  {PERMISSION_MODULES.map(m => {
                    const p = emp.permissions[m.key];
                    if (!p || !p.view) return null;
                    return (
                      <span key={m.key} className={`text-xs px-2 py-0.5 rounded-full ${p.action ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}`} data-testid={`perm-badge-${emp.id}-${m.key}`}>
                        {m.label} {p.action ? '(Full)' : '(View)'}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Link Modal */}
      {showLinkModal && linkTarget && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="link-modal">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[85vh] overflow-y-auto p-5 space-y-4">
            <h3 className="font-semibold text-gray-900">Link Employee</h3>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-sm font-medium">{linkTarget.name || linkTarget.email}</p>
              <p className="text-xs text-gray-500">{linkTarget.email}</p>
            </div>

            {/* Role Selection */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Role Template</label>
              <select value={linkRole} onChange={e => applyTemplate(e.target.value, setLinkPerms, setLinkRole)} className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="link-role-select">
                <option value="">Select a role template...</option>
                {Object.keys(roleTemplates).map(r => <option key={r} value={r}>{r}</option>)}
              </select>
              <p className="text-xs text-gray-400 mt-1">Select a template to pre-fill permissions, then customize as needed.</p>
            </div>

            {/* Custom Role Name */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Role Name</label>
              <input type="text" value={linkRole} onChange={e => setLinkRole(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="e.g. Sales Executive" data-testid="link-role-name" />
            </div>

            {/* Permissions */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">Permissions</label>
              <PermissionGrid perms={linkPerms} onChange={setLinkPerms} />
            </div>

            <div className="flex justify-end gap-3 pt-2 border-t">
              <button onClick={() => setShowLinkModal(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={handleLink} disabled={linking || !linkRole} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1" data-testid="confirm-link-btn">
                {linking ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />} Link Employee
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editEmployee && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="edit-modal">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[85vh] overflow-y-auto p-5 space-y-4">
            <h3 className="font-semibold text-gray-900">Edit Access — {editEmployee.name || editEmployee.email}</h3>

            {/* Status */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Status</label>
              <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="edit-status">
                <option value="active">Active</option>
                <option value="disabled">Disabled (Login allowed, no system access)</option>
              </select>
            </div>

            {/* Role */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Role</label>
              <div className="flex gap-2">
                <select value={Object.keys(roleTemplates).includes(editRole) ? editRole : ''} onChange={e => { if (e.target.value) applyTemplate(e.target.value, setEditPerms, setEditRole); }} className="flex-1 px-3 py-2 border rounded-lg text-sm" data-testid="edit-role-template">
                  <option value="">Apply template...</option>
                  {Object.keys(roleTemplates).map(r => <option key={r} value={r}>{r}</option>)}
                </select>
                <input type="text" value={editRole} onChange={e => setEditRole(e.target.value)} className="flex-1 px-3 py-2 border rounded-lg text-sm" placeholder="Custom role" data-testid="edit-role-name" />
              </div>
            </div>

            {/* Permissions */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">Permissions</label>
              <PermissionGrid perms={editPerms} onChange={setEditPerms} />
            </div>

            <div className="flex justify-end gap-3 pt-2 border-t">
              <button onClick={() => setEditEmployee(null)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
              <button onClick={handleSaveEdit} disabled={saving} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1" data-testid="save-edit-btn">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />} Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Logs Modal */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="logs-modal">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[85vh] overflow-y-auto p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><History className="w-4 h-4" /> Audit Logs</h3>
              <button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
            </div>
            {logs.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">No logs yet</p>
            ) : (
              <div className="space-y-2">
                {logs.map((log, i) => (
                  <div key={i} className="text-xs border-b pb-2">
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${(log.action as string) === 'unlinked' ? 'text-red-600' : (log.action as string) === 'linked' ? 'text-green-600' : 'text-blue-600'}`}>
                        {(log.action as string)?.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="text-gray-400">{log.timestamp ? new Date(log.timestamp as string).toLocaleString('en-IN') : ''}</span>
                    </div>
                    {log.details && <p className="text-gray-600 mt-0.5">{log.details as string}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
