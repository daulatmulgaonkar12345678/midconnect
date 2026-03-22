'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePermissions } from '../layout';
import { toast } from 'sonner';
import {
  Zap, Plus, Pencil, Trash2, Loader2, X, Save, Power, PowerOff,
  ChevronRight, Activity, AlertTriangle, Lock
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Not Equals' },
  { value: 'greater_than', label: 'Greater Than' },
  { value: 'less_than', label: 'Less Than' },
  { value: 'contains', label: 'Contains' },
  { value: 'not_empty', label: 'Not Empty' },
  { value: 'is_empty', label: 'Is Empty' },
];

const OPERATIONS = [
  { value: 'increment', label: 'Increment (+)' },
  { value: 'decrement', label: 'Decrement (-)' },
  { value: 'set_value', label: 'Set Value (=)' },
];

interface PanelField {
  key: string;
  label: string;
  type: string;
  relatedPanel?: string;
  options?: string[];
  systemManaged?: boolean;
  bindingField?: string;
}

interface Panel {
  id: string;
  name: string;
  fields: PanelField[];
}

interface AutomationRule {
  id: string;
  name: string;
  trigger_panel_id: string;
  trigger_panel_name?: string;
  condition: { field: string; operator: string; value?: string };
  actions: {
    type: string;
    target_panel_id: string;
    target_panel_name?: string;
    target_panel_type: string;
    relation_field: string;
    operation?: string;
    field?: string;
    value_from?: string;
  }[];
  is_active: boolean;
  execution_count: number;
  last_executed?: string;
}

interface AutoLog {
  ruleName: string;
  status: string;
  action: string;
  operation?: string;
  field?: string;
  value_applied?: string;
  timestamp: string;
  error?: string;
}

export default function AutomationPage() {
  const { token, isAdmin, loading: permLoading } = usePermissions();
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [logs, setLogs] = useState<AutoLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLogs, setShowLogs] = useState(false);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);
  const [ruleName, setRuleName] = useState('');
  const [triggerPanelId, setTriggerPanelId] = useState('');
  const [condField, setCondField] = useState('');
  const [condOp, setCondOp] = useState('equals');
  const [condValue, setCondValue] = useState('');
  const [actionType, setActionType] = useState('update_related');
  const [actionRelField, setActionRelField] = useState('');
  const [actionOp, setActionOp] = useState('increment');
  const [actionField, setActionField] = useState('');
  const [actionValueFrom, setActionValueFrom] = useState('');
  const [saving, setSaving] = useState(false);

  const headers = useCallback(() => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }), [token]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [rulesRes, panelsRes] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/automation/rules`, { headers: headers() }),
        fetch(`${API_URL}/api/business-tools/panels`, { headers: headers() }),
      ]);
      if (rulesRes.ok) { const d = await rulesRes.json(); setRules(d.rules || []); }
      if (panelsRes.ok) { const d = await panelsRes.json(); setPanels(d.panels || []); }
    } catch { /* empty */ }
    setLoading(false);
  }, [token, headers]);

  useEffect(() => {
    if (!permLoading && token) fetchData();
  }, [permLoading, token, fetchData]);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/automation/logs`, { headers: headers() });
      if (res.ok) { const d = await res.json(); setLogs(d.logs || []); }
    } catch { /* empty */ }
    setShowLogs(true);
  };

  const triggerPanel = panels.find(p => p.id === triggerPanelId);
  const triggerFields = triggerPanel?.fields || [];
  const relationFields = triggerFields.filter(f => f.type === 'relation');

  // Condition field info (for showing dropdown options)
  const condFieldInfo = triggerFields.find(f => f.key === condField);
  const condFieldHasOptions = condFieldInfo && (condFieldInfo.type === 'dropdown' || condFieldInfo.type === 'multiselect') && condFieldInfo.options?.length;

  const SYSTEM_MODULES = ['inventory', 'invoices', 'buyers', 'suppliers', 'purchase_orders', 'quotations', 'composite_products', 'employees'];
  const MODULE_LABELS: Record<string, string> = {
    inventory: 'Inventory', invoices: 'Invoices', buyers: 'Buyers',
    suppliers: 'Suppliers', purchase_orders: 'Purchase Orders',
    quotations: 'Quotations', composite_products: 'Composite Products', employees: 'Employees',
  };

  // Fields available on the target panel (for the Target Field dropdown)
  const SYSTEM_TARGET_FIELDS: Record<string, { key: string; label: string }[]> = {
    inventory: [
      { key: 'stock', label: 'Stock' },
      { key: 'quantity', label: 'Quantity' },
      { key: 'minStock', label: 'Min Stock' },
      { key: 'reorderPoint', label: 'Reorder Point' },
    ],
  };

  // Derive target panel from selected relation field (auto-set)
  const selectedRelField = triggerFields.find(f => f.key === actionRelField);
  const derivedTargetId = selectedRelField?.relatedPanel || '';
  const derivedTargetType = SYSTEM_MODULES.includes(derivedTargetId) ? 'system' : 'custom';
  const derivedTargetName = SYSTEM_MODULES.includes(derivedTargetId)
    ? MODULE_LABELS[derivedTargetId] || derivedTargetId
    : panels.find(p => p.id === derivedTargetId)?.name || derivedTargetId;

  const targetPanelFields = (() => {
    if (!derivedTargetId) return [];
    if (derivedTargetType === 'system') {
      return SYSTEM_TARGET_FIELDS[derivedTargetId] || [];
    }
    const tp = panels.find(p => p.id === derivedTargetId);
    return (tp?.fields || [])
      .filter(f => f.type !== 'relation')
      .map(f => ({ key: f.key, label: f.label }));
  })();

  const resetForm = () => {
    setRuleName(''); setTriggerPanelId(''); setCondField(''); setCondOp('equals'); setCondValue('');
    setActionType('update_related');
    setActionRelField(''); setActionOp('increment'); setActionField(''); setActionValueFrom('');
  };

  const openCreate = () => { setEditingRule(null); resetForm(); setShowModal(true); };

  const openEdit = (rule: AutomationRule) => {
    setEditingRule(rule);
    setRuleName(rule.name);
    setTriggerPanelId(rule.trigger_panel_id);
    setCondField(rule.condition.field);
    setCondOp(rule.condition.operator);
    setCondValue(rule.condition.value || '');
    const a = rule.actions[0];
    if (a) {
      setActionType(a.type);
      setActionRelField(a.relation_field);
      setActionOp(a.operation || 'increment');
      setActionField(a.field || '');
      setActionValueFrom(a.value_from || '');
    }
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!ruleName.trim()) { toast.error('Rule name is required'); return; }
    if (!triggerPanelId) { toast.error('Select a trigger panel'); return; }
    if (!condField) { toast.error('Select a condition field'); return; }
    if (!actionRelField) { toast.error('Select a relation field for action'); return; }
    if (!derivedTargetId) { toast.error('Relation field has no linked target'); return; }
    if (actionType === 'update_related' && !actionField) { toast.error('Select a target field'); return; }
    if (actionType === 'update_related' && !actionValueFrom) { toast.error('Select a value source field'); return; }

    setSaving(true);
    const body = {
      name: ruleName.trim(),
      trigger_panel_id: triggerPanelId,
      condition: { field: condField, operator: condOp, value: condValue || undefined },
      actions: [{
        type: actionType,
        target_panel_id: derivedTargetId,
        target_panel_type: derivedTargetType,
        relation_field: actionRelField,
        operation: actionType === 'update_related' ? actionOp : undefined,
        field: actionField || undefined,
        value_from: actionValueFrom || undefined,
      }],
    };

    try {
      const url = editingRule
        ? `${API_URL}/api/business-tools/automation/rules/${editingRule.id}`
        : `${API_URL}/api/business-tools/automation/rules`;
      const res = await fetch(url, {
        method: editingRule ? 'PUT' : 'POST',
        headers: headers(),
        body: JSON.stringify(body),
      });
      if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Failed'); setSaving(false); return; }
      toast.success(editingRule ? 'Rule updated' : 'Rule created');
      setShowModal(false);
      fetchData();
    } catch { toast.error('Operation failed'); }
    setSaving(false);
  };

  const toggleRule = async (rule: AutomationRule) => {
    try {
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${rule.id}`, {
        method: 'PUT', headers: headers(),
        body: JSON.stringify({ is_active: !rule.is_active }),
      });
      if (res.ok) { toast.success(rule.is_active ? 'Rule disabled' : 'Rule enabled'); fetchData(); }
    } catch { toast.error('Toggle failed'); }
  };

  const deleteRule = async (rule: AutomationRule) => {
    if (!confirm(`Delete rule "${rule.name}"?`)) return;
    try {
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${rule.id}`, {
        method: 'DELETE', headers: headers(),
      });
      if (res.ok) { toast.success('Rule deleted'); fetchData(); }
    } catch { toast.error('Delete failed'); }
  };

  if (permLoading || loading) {
    return <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
  }

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center" data-testid="automation-restricted">
        <Lock className="h-10 w-10 text-amber-500 mb-3" />
        <h2 className="text-xl font-bold text-gray-900">Admin Access Required</h2>
        <p className="text-gray-500 mt-2">Only business admins can manage automation rules.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="automation-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2" data-testid="automation-heading">
            <Zap className="h-6 w-6 text-amber-500" /> Workflow Automation
          </h1>
          <p className="text-gray-500 mt-1 text-sm">Create rules to automate actions across your panels.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchLogs}
            className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50"
            data-testid="view-logs-btn"
          >
            <Activity className="h-4 w-4" /> Logs
          </button>
          <button onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700"
            data-testid="create-rule-btn"
          >
            <Plus className="h-4 w-4" /> New Rule
          </button>
        </div>
      </div>

      {/* Safety notice */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3" data-testid="safety-notice">
        <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-amber-800">
          <strong>Safety:</strong> Automation rules only run on <strong>custom panels</strong>. System modules (Invoices, PO, etc.) are protected. Updates happen through relation fields only — no blind or global updates.
        </div>
      </div>

      {/* Rules list */}
      {rules.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="empty-rules">
          <Zap className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-700">No automation rules</h3>
          <p className="text-gray-400 text-sm mt-1 max-w-sm mx-auto">
            Create rules like &quot;If QC Status = Passed → Increment Inventory Stock&quot;.
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="rules-list">
          {rules.map(rule => (
            <div key={rule.id} className={`bg-white rounded-xl border p-4 transition-all ${rule.is_active ? '' : 'opacity-60'}`} data-testid={`rule-card-${rule.id}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${rule.is_active ? 'bg-amber-100' : 'bg-gray-100'}`}>
                    <Zap className={`h-4.5 w-4.5 ${rule.is_active ? 'text-amber-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 text-sm">{rule.name}</h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      When <strong>{rule.trigger_panel_name}</strong> → {rule.condition.field} {rule.condition.operator} {rule.condition.value || ''} → {rule.actions[0]?.operation || rule.actions[0]?.type} on <strong>{rule.actions[0]?.target_panel_name}</strong>
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{rule.execution_count} runs</span>
                  <button onClick={() => toggleRule(rule)}
                    className={`p-1.5 rounded-lg transition-colors ${rule.is_active ? 'text-green-600 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'}`}
                    data-testid={`toggle-rule-${rule.id}`}
                    title={rule.is_active ? 'Disable' : 'Enable'}
                  >
                    {rule.is_active ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />}
                  </button>
                  <button onClick={() => openEdit(rule)}
                    className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg"
                    data-testid={`edit-rule-${rule.id}`}
                  >
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button onClick={() => deleteRule(rule)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    data-testid={`delete-rule-${rule.id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Logs modal */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowLogs(false)}>
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="logs-modal">
            <div className="p-5 border-b flex items-center justify-between sticky top-0 bg-white z-10 rounded-t-xl">
              <h2 className="text-lg font-bold text-gray-900">Automation Logs</h2>
              <button onClick={() => setShowLogs(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-500" /></button>
            </div>
            <div className="p-5 space-y-2">
              {logs.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">No execution logs yet.</p>
              ) : logs.map((log, i) => (
                <div key={i} className={`px-3 py-2 rounded-lg border text-sm ${log.status === 'error' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{log.ruleName}</span>
                    <span className="text-xs text-gray-400">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</span>
                  </div>
                  {log.status === 'error' ? (
                    <p className="text-red-600 text-xs mt-1">{log.error}</p>
                  ) : (
                    <p className="text-green-700 text-xs mt-1">{log.operation} → {log.field} = {log.value_applied}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl w-full max-w-xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="rule-modal">
            <div className="p-5 border-b sticky top-0 bg-white z-10 rounded-t-xl">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">{editingRule ? 'Edit Rule' : 'Create Automation Rule'}</h2>
                <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-500" /></button>
              </div>
            </div>

            <div className="p-5 space-y-5">
              {/* Rule name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name *</label>
                <input type="text" value={ruleName} onChange={e => setRuleName(e.target.value)}
                  placeholder="e.g. QC Passed → Add to Inventory"
                  className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="rule-name-input" />
              </div>

              {/* Trigger panel */}
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 space-y-3">
                <label className="block text-sm font-semibold text-blue-800">WHEN (Trigger Panel)</label>
                <select value={triggerPanelId} onChange={e => { setTriggerPanelId(e.target.value); setCondField(''); setActionRelField(''); }}
                  className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="trigger-panel-select">
                  <option value="">Select custom panel...</option>
                  {panels.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
                <p className="text-xs text-blue-600">Only custom panels can trigger automation.</p>
              </div>

              {/* Condition */}
              {triggerPanelId && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 space-y-3">
                  <label className="block text-sm font-semibold text-amber-800">IF (Condition)</label>
                  <div className="grid grid-cols-3 gap-2">
                    <select value={condField} onChange={e => { setCondField(e.target.value); setCondValue(''); }}
                      className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-field-select">
                      <option value="">Field...</option>
                      {triggerFields.filter(f => f.type !== 'relation').map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                    </select>
                    <select value={condOp} onChange={e => setCondOp(e.target.value)}
                      className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-op-select">
                      {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    {!['not_empty', 'is_empty'].includes(condOp) && (
                      condFieldHasOptions ? (
                        <select value={condValue} onChange={e => setCondValue(e.target.value)}
                          className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-value-select">
                          <option value="">Select value...</option>
                          {condFieldInfo!.options!.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <input type="text" value={condValue} onChange={e => setCondValue(e.target.value)}
                          placeholder="Value" className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-value-input" />
                      )
                    )}
                  </div>
                </div>
              )}

              {/* Action */}
              {triggerPanelId && condField && (
                <div className="p-3 bg-green-50 rounded-lg border border-green-200 space-y-3">
                  <label className="block text-sm font-semibold text-green-800">THEN (Action)</label>

                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Via Relation Field *</label>
                    <select value={actionRelField} onChange={e => { setActionRelField(e.target.value); setActionField(''); }}
                      className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="action-rel-field-select">
                      <option value="">Select relation field...</option>
                      {relationFields.map(f => {
                        const targetLabel = SYSTEM_MODULES.includes(f.relatedPanel || '')
                          ? MODULE_LABELS[f.relatedPanel || ''] || f.relatedPanel
                          : panels.find(p => p.id === f.relatedPanel)?.name || f.relatedPanel;
                        const binding = f.bindingField ? ` via ${f.bindingField}` : '';
                        return <option key={f.key} value={f.key}>{f.label} (→ {targetLabel}{binding})</option>;
                      })}
                    </select>
                  </div>

                  {/* Target Panel — auto-derived from relation field (read-only) */}
                  {actionRelField && derivedTargetId && (
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Target Panel (auto-detected)</label>
                      <div className="w-full px-3 py-2 bg-white border rounded-lg text-sm text-gray-700 flex items-center gap-2" data-testid="action-target-display">
                        <Lock className="h-3.5 w-3.5 text-gray-400" />
                        <span className="font-medium">{derivedTargetName}</span>
                        <span className="text-xs text-gray-400 ml-auto">{derivedTargetType === 'system' ? 'System Module' : 'Custom Panel'}</span>
                      </div>
                    </div>
                  )}

                  {actionRelField && derivedTargetId && (
                    <>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Operation *</label>
                          <select value={actionOp} onChange={e => setActionOp(e.target.value)}
                            className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="action-op-select">
                            {OPERATIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Target Field *</label>
                          <select value={actionField} onChange={e => setActionField(e.target.value)}
                            className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="action-field-select">
                            <option value="">Select target field...</option>
                            {targetPanelFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Value From (trigger field) *</label>
                        <select value={actionValueFrom} onChange={e => setActionValueFrom(e.target.value)}
                          className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="action-value-from-select">
                          <option value="">Select field...</option>
                          {triggerFields.filter(f => f.type !== 'relation').map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                        </select>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            <div className="p-5 border-t bg-gray-50/50 rounded-b-xl flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 px-5 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
                data-testid="save-rule-btn">
                <Save className="h-4 w-4" /> {saving ? 'Saving...' : editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
