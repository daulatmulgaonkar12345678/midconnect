'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import {
  Users, Search, UserPlus, UserMinus, Shield, Loader2,
  Mail, Phone, Clock, AlertTriangle, CheckCircle, XCircle, Settings, Eye, Pencil, History, LayoutGrid, Plus
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface ModulePerm { view: boolean; edit: boolean; }
interface PanelPerm { canView: boolean; canCreate: boolean; canEdit: boolean; }
interface EmpPerms { modules: Record<string, ModulePerm>; panels: Record<string, PanelPerm>; }
interface Employee {
  id: string; email: string; name: string; phone: string;
  role: string; status: string; permissions: EmpPerms;
  linkedAt: string; unlinkedAt: string; createdAt: string;
}
interface ModuleItem { id: string; name: string; }
interface PanelItem { id: string; name: string; color: string; }

type Tab = 'active' | 'pending' | 'unlinked';

const PANEL_COLOR_DOT: Record<string, string> = {
  blue: 'bg-blue-500', red: 'bg-red-500', green: 'bg-green-500',
  purple: 'bg-purple-500', orange: 'bg-orange-500', amber: 'bg-amber-500',
  cyan: 'bg-cyan-500', pink: 'bg-pink-500', indigo: 'bg-indigo-500',
  violet: 'bg-violet-500', slate: 'bg-slate-500',
};

function normalizeModPerms(raw: Record<string, unknown>): Record<string, ModulePerm> {
  const out: Record<string, ModulePerm> = {};
  for (const [k, v] of Object.entries(raw || {})) {
    if (typeof v === 'boolean') out[k] = { view: v, edit: v };
    else if (v && typeof v === 'object') {
      const o = v as Record<string, boolean>;
      out[k] = { view: o.view === true, edit: o.edit === true || o.action === true };
    }
  }
  return out;
}

export default function EmployeeManagementPage() {
  const { getIdToken } = useAuth();
  const [tab, setTab] = useState<Tab>('active');
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleTemplates, setRoleTemplates] = useState<Record<string, EmpPerms>>({});
  const [allModules, setAllModules] = useState<ModuleItem[]>([]);
  const [allPanels, setAllPanels] = useState<PanelItem[]>([]);
  const [searchEmail, setSearchEmail] = useState('');
  const [searchResult, setSearchResult] = useState<Record<string, unknown> | null>(null);
  const [searching, setSearching] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkTarget, setLinkTarget] = useState<{ id: string; email: string; name: string } | null>(null);
  const [linkRole, setLinkRole] = useState('');
  const [linkPerms, setLinkPerms] = useState<EmpPerms>({ modules: {}, panels: {} });
  const [linking, setLinking] = useState(false);
  const [editEmployee, setEditEmployee] = useState<Employee | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editPerms, setEditPerms] = useState<EmpPerms>({ modules: {}, panels: {} });
  const [editStatus, setEditStatus] = useState('');
  const [saving, setSaving] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<Record<string, unknown>[]>([]);

  const authHeaders = useCallback(async () => {
    const token = await getIdToken();
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  const fetchEmployees = useCallback(async () => {
    setLoading(true); setEmployees([]);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/list?tab=${tab}`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        // Normalize module permissions for each employee
        const emps = (data.employees || []).map((e: Employee) => {
          const p = e.permissions || { modules: {}, panels: {} };
          return { ...e, permissions: { modules: normalizeModPerms(p.modules || {}), panels: p.panels || {} } };
        });
        setEmployees(emps);
      }
    } catch { /* empty */ }
    setLoading(false);
  }, [authHeaders, tab]);

  const fetchTemplates = useCallback(async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/role-templates`, { headers: h });
      if (res.ok) {
        const data = await res.json();
        // Normalize template modules to {view, edit}
        const tpls: Record<string, EmpPerms> = {};
        for (const [name, val] of Object.entries(data.templates || {})) {
          const t = val as EmpPerms;
          tpls[name] = { modules: normalizeModPerms(t.modules || {}), panels: t.panels || {} };
        }
        setRoleTemplates(tpls);
      }
    } catch { /* empty */ }
  }, [authHeaders]);

  const fetchModulesAndPanels = useCallback(async () => {
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/modules`, { headers: h });
      if (res.ok) { const data = await res.json(); setAllModules(data.modules || []); setAllPanels(data.panels || []); }
    } catch { /* empty */ }
  }, [authHeaders]);

  useEffect(() => { fetchEmployees(); }, [fetchEmployees]);
  useEffect(() => { fetchTemplates(); fetchModulesAndPanels(); }, [fetchTemplates, fetchModulesAndPanels]);

  const initPerms = useCallback((): EmpPerms => ({
    modules: Object.fromEntries(allModules.map(m => [m.id, { view: false, edit: false }])),
    panels: Object.fromEntries(allPanels.map(p => [p.id, { canView: false, canCreate: false, canEdit: false }])),
  }), [allModules, allPanels]);

  const handleSearch = async () => {
    if (!searchEmail.trim()) { toast.error('Enter an email'); return; }
    setSearching(true); setSearchResult(null);
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/search?email=${encodeURIComponent(searchEmail.trim())}`, { headers: h });
      setSearchResult(await res.json());
    } catch { toast.error('Search failed'); }
    setSearching(false);
  };

  const openLinkModal = (user: Record<string, unknown>) => {
    setLinkTarget({ id: user.id as string, email: user.email as string, name: user.name as string });
    setLinkRole(''); setLinkPerms(initPerms()); setShowLinkModal(true);
  };

  const applyTemplate = (templateName: string, setter: (p: EmpPerms) => void, roleSetter: (r: string) => void) => {
    const tpl = roleTemplates[templateName];
    if (tpl) {
      const perms: EmpPerms = { modules: {}, panels: {} };
      allModules.forEach(m => { perms.modules[m.id] = tpl.modules?.[m.id] || { view: false, edit: false }; });
      allPanels.forEach(p => { perms.panels[p.id] = { canView: false, canCreate: false, canEdit: false }; });
      setter(perms); roleSetter(templateName);
    }
  };

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
      setShowLinkModal(false); setSearchResult(null); setSearchEmail('');
      fetchEmployees();
    } catch { toast.error('Link failed'); }
    setLinking(false);
  };

  const handleUnlink = async (id: string) => {
    if (!confirm('Unlink this employee? Their access will be revoked immediately.')) return;
    try {
      const h = await authHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/employee-mgmt/${id}/unlink`, { method: 'POST', headers: h });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Failed'); return; }
      toast.success(data.message); fetchEmployees();
    } catch { toast.error('Unlink failed'); }
  };

  const openEdit = (emp: Employee) => {
    setEditEmployee(emp); setEditRole(emp.role); setEditStatus(emp.status);
    const perms: EmpPerms = { modules: {}, panels: {} };
    const ep = emp.permissions || { modules: {}, panels: {} };
    allModules.forEach(m => { perms.modules[m.id] = ep.modules?.[m.id] || { view: false, edit: false }; });
    allPanels.forEach(p => {
      const pp = ep.panels?.[p.id];
      perms.panels[p.id] = { canView: pp?.canView || false, canCreate: pp?.canCreate || false, canEdit: pp?.canEdit || false };
    });
    setEditPerms(perms);
  };

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
      toast.success('Access updated'); setEditEmployee(null); fetchEmployees();
    } catch { toast.error('Update failed'); }
    setSaving(false);
  };

  const handleRelink = (emp: Employee) => {
    setLinkTarget({ id: emp.id, email: emp.email, name: emp.name });
    setLinkRole(''); setLinkPerms(initPerms()); setShowLinkModal(true);
  };

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

  const PermissionGrid = ({ perms, onChange, disabled }: { perms: EmpPerms; onChange: (p: EmpPerms) => void; disabled?: boolean }) => (
    <div className="space-y-4" data-testid="permission-grid">
      {/* System Modules with View/Edit */}
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Shield className="w-3 h-3" /> Module Access
        </h4>
        <div className="space-y-0.5">
          {allModules.map(m => {
            const mp = perms.modules?.[m.id] || { view: false, edit: false };
            return (
              <div key={m.id} className="flex items-center justify-between py-1.5 hover:bg-gray-50 rounded px-2" data-testid={`perm-row-${m.id}`}>
                <span className="text-sm text-gray-700 min-w-[120px]">{m.name}</span>
                <div className="flex gap-3">
                  <label className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer select-none">
                    <input type="checkbox" checked={mp.view} disabled={disabled}
                      onChange={e => {
                        const nv = e.target.checked;
                        const np = { ...perms, modules: { ...perms.modules, [m.id]: { view: nv, edit: nv ? mp.edit : false } } };
                        onChange(np);
                      }}
                      className="w-3.5 h-3.5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
                      data-testid={`perm-module-${m.id}-view`} />
                    <Eye className="w-3 h-3" /> View
                  </label>
                  <label className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer select-none">
                    <input type="checkbox" checked={mp.edit} disabled={disabled || !mp.view}
                      onChange={e => {
                        const np = { ...perms, modules: { ...perms.modules, [m.id]: { ...mp, edit: e.target.checked } } };
                        onChange(np);
                      }}
                      className="w-3.5 h-3.5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 disabled:opacity-30"
                      data-testid={`perm-module-${m.id}-edit`} />
                    <Pencil className="w-3 h-3" /> Edit
                  </label>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Custom Panels */}
      {allPanels.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <LayoutGrid className="w-3 h-3" /> Custom Panels
          </h4>
          <div className="space-y-2">
            {allPanels.map(p => {
              const pp = perms.panels?.[p.id] || { canView: false, canCreate: false, canEdit: false };
              return (
                <div key={p.id} className="border border-gray-200 rounded-lg p-3" data-testid={`perm-panel-${p.id}`}>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${PANEL_COLOR_DOT[p.color] || 'bg-blue-500'}`} />
                    <span className="text-sm font-medium text-gray-800">{p.name}</span>
                  </div>
                  <div className="flex gap-4 ml-5">
                    {([['canView', 'View', Eye], ['canCreate', 'Create', Plus], ['canEdit', 'Edit', Pencil]] as const).map(([key, label, Icon]) => (
                      <label key={key} className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
                        <input type="checkbox" checked={pp[key as keyof PanelPerm] || false}
                          disabled={disabled || (key !== 'canView' && !pp.canView)}
                          onChange={e => {
                            const newPP = { ...pp, [key]: e.target.checked };
                            if (key === 'canView' && !e.target.checked) { newPP.canCreate = false; newPP.canEdit = false; }
                            onChange({ ...perms, panels: { ...perms.panels, [p.id]: newPP } });
                          }}
                          className="w-3.5 h-3.5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 disabled:opacity-30"
                          data-testid={`perm-panel-${p.id}-${key}`} />
                        <Icon className="w-3 h-3" /> {label}
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );

  const moduleNameMap = useMemo(() => Object.fromEntries(allModules.map(m => [m.id, m.name])), [allModules]);

  return (
    <div className="space-y-4" data-testid="employee-mgmt-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900" data-testid="employee-heading">Employee Management</h2>
          <p className="text-sm text-gray-500">Link, manage, and control employee access in real-time</p>
        </div>
        <button onClick={fetchLogs} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200" data-testid="view-logs-btn">
          <History className="w-3.5 h-3.5" /> Audit Logs
        </button>
      </div>

      {/* Search + Link */}
      <div className="bg-white rounded-xl border p-4 space-y-3" data-testid="search-section">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2"><UserPlus className="w-4 h-4 text-indigo-600" /> Link New Employee</h3>
        <p className="text-xs text-gray-500">Search by email. They must have a buyer account first.</p>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="email" value={searchEmail} onChange={e => setSearchEmail(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="Enter employee email..." className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm" data-testid="search-email-input" />
          </div>
          <button onClick={handleSearch} disabled={searching} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5" data-testid="search-btn">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Search
          </button>
        </div>
        {searchResult && (
          <div className="mt-2 p-3 rounded-lg border bg-gray-50" data-testid="search-result">
            {!searchResult.found && <div className="flex items-center gap-2 text-sm text-amber-700"><AlertTriangle className="w-4 h-4" /><span>{searchResult.message as string}</span></div>}
            {Boolean(searchResult.found) && Boolean(searchResult.alreadyLinked) && <div className="flex items-center gap-2 text-sm text-blue-700"><CheckCircle className="w-4 h-4" /><span>{String(searchResult.message || '')}</span></div>}
            {Boolean(searchResult.found) && Boolean(searchResult.linkedElsewhere) && <div className="flex items-center gap-2 text-sm text-red-700"><XCircle className="w-4 h-4" /><span>{String(searchResult.message || '')}</span></div>}
            {Boolean(searchResult.found) && Boolean(searchResult.canLink) && (
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">{(searchResult.user as Record<string, unknown>)?.name as string || 'No name'}</p>
                  <p className="text-xs text-gray-500">{(searchResult.user as Record<string, unknown>)?.email as string}</p>
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
          <button key={key} onClick={() => setTab(key)} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-colors ${tab === key ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`} data-testid={`tab-${key}`}>
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
          <p className="text-gray-500 text-sm">{tab === 'active' ? 'No active employees.' : tab === 'pending' ? 'No pending users.' : 'No unlinked employees.'}</p>
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
                    {emp.role && emp.role !== 'unassigned' && <span className="text-xs text-indigo-600 font-medium flex items-center gap-1 mt-0.5"><Shield className="w-3 h-3" /> {emp.role}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {tab === 'active' && (
                    <>
                      <button onClick={() => openEdit(emp)} className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200 flex items-center gap-1" data-testid={`edit-access-${emp.id}`}><Settings className="w-3.5 h-3.5" /> Edit Access</button>
                      <button onClick={() => handleUnlink(emp.id)} className="px-3 py-1.5 text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium flex items-center gap-1" data-testid={`unlink-${emp.id}`}><UserMinus className="w-3.5 h-3.5" /> Unlink</button>
                    </>
                  )}
                  {tab === 'pending' && <button onClick={() => openLinkModal({ id: emp.id, email: emp.email, name: emp.name } as Record<string, unknown>)} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 flex items-center gap-1" data-testid={`link-pending-${emp.id}`}><UserPlus className="w-3.5 h-3.5" /> Link</button>}
                  {tab === 'unlinked' && <button onClick={() => handleRelink(emp)} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 flex items-center gap-1" data-testid={`relink-${emp.id}`}><UserPlus className="w-3.5 h-3.5" /> Re-link</button>}
                </div>
              </div>
              {/* Permission badges */}
              {tab === 'active' && emp.permissions && (
                <div className="mt-2 flex flex-wrap gap-1.5 pt-2 border-t">
                  {allModules.map(m => {
                    const mp = emp.permissions.modules?.[m.id];
                    if (!mp?.view) return null;
                    return (
                      <span key={m.id} className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700" data-testid={`perm-badge-${emp.id}-${m.id}`}>
                        {m.name} {mp.edit ? '(V+E)' : '(V)'}
                      </span>
                    );
                  })}
                  {allPanels.map(p => {
                    const pp = emp.permissions.panels?.[p.id];
                    if (!pp?.canView) return null;
                    const lvls = [pp.canView && 'V', pp.canCreate && 'C', pp.canEdit && 'E'].filter(Boolean).join('');
                    return <span key={p.id} className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700" data-testid={`perm-badge-${emp.id}-panel-${p.id}`}>{p.name} ({lvls})</span>;
                  })}
                  {!allModules.some(m => emp.permissions.modules?.[m.id]?.view) && !allPanels.some(p => emp.permissions.panels?.[p.id]?.canView) && <span className="text-xs text-gray-400 italic">No permissions assigned</span>}
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
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Role Template</label>
              <select value={linkRole} onChange={e => applyTemplate(e.target.value, setLinkPerms, setLinkRole)} className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="link-role-select">
                <option value="">Select a role template...</option>
                {Object.keys(roleTemplates).map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Role Name</label>
              <input type="text" value={linkRole} onChange={e => setLinkRole(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" placeholder="e.g. Sales Executive" data-testid="link-role-name" />
            </div>
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
            <h3 className="font-semibold text-gray-900">Edit Access &mdash; {editEmployee.name || editEmployee.email}</h3>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Status</label>
              <select value={editStatus} onChange={e => setEditStatus(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="edit-status">
                <option value="active">Active</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
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

      {/* Audit Logs */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" data-testid="logs-modal">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[85vh] overflow-y-auto p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2"><History className="w-4 h-4" /> Audit Logs</h3>
              <button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-gray-600 text-lg">&times;</button>
            </div>
            {logs.length === 0 ? <p className="text-sm text-gray-500 text-center py-4">No logs yet</p> : (
              <div className="space-y-2">
                {logs.map((log, i) => (
                  <div key={i} className="text-xs border-b pb-2">
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${(log.action as string) === 'unlinked' ? 'text-red-600' : (log.action as string) === 'linked' ? 'text-green-600' : 'text-blue-600'}`}>{(log.action as string)?.replace('_', ' ').toUpperCase()}</span>
                      <span className="text-gray-400">{log.timestamp ? new Date(log.timestamp as string).toLocaleString('en-IN') : ''}</span>
                    </div>
                    {log.details ? <p className="text-gray-600 mt-0.5">{String(log.details)}</p> : null}
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
