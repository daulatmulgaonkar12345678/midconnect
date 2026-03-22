'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import {
  Zap, Plus, Pencil, Trash2, Loader2, X, Save, Power, PowerOff,
  ChevronRight, Activity, AlertTriangle, Lock, Check, ChevronsUpDown
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

const TRIGGER_TYPES = [
  { value: 'on_create', label: 'On Create (New Record)' },
  { value: 'on_update', label: 'On Update (Record Changed)' },
  { value: 'condition_based', label: 'Condition Based' },
];

const ACTION_TYPES = [
  { value: 'create_record', label: 'Create Record' },
  { value: 'create_records_per_item', label: 'Create Records (Per Item)' },
  { value: 'update_record', label: 'Update Record' },
];

const OPERATORS = [
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Not Equals' },
  { value: 'greater_than', label: 'Greater Than' },
  { value: 'less_than', label: 'Less Than' },
  { value: 'contains', label: 'Contains' },
  { value: 'not_empty', label: 'Not Empty' },
  { value: 'is_empty', label: 'Is Empty' },
];

const UPDATE_OPS = [
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
  allowedModules?: string[];
  allowedPanels?: string[];
}

interface AutomationRule {
  id: string;
  name: string;
  trigger_panel_id: string;
  trigger_panel_name?: string;
  trigger_type: string;
  condition?: { field: string; operator: string; value?: string };
  action_type: string;
  target_panel_id: string;
  target_panel_name?: string;
  relation_field: string;
  update_operation?: string;
  update_field?: string;
  update_value_from?: string;
  field_mappings?: { target_field: string; source_field?: string; default_value?: string; mapping_type: string }[];
  field_visibility?: { field: string; visible: boolean; editable: boolean }[];
  is_active: boolean;
  execution_count: number;
  last_executed?: string;
  priority: number;
}

const SYSTEM_MODULES = ['inventory', 'invoices', 'buyers', 'suppliers', 'purchase_orders', 'quotations', 'composite_products', 'employees'];
const MODULE_LABELS: Record<string, string> = {
  inventory: 'Inventory', invoices: 'Invoices', buyers: 'Buyers',
  suppliers: 'Suppliers', purchase_orders: 'Purchase Orders',
  quotations: 'Quotations', composite_products: 'Composite Products', employees: 'Employees',
};

export default function AutomationPage() {
  const { getIdToken } = useAuth();
  const [panels, setPanels] = useState<Panel[]>([]);
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<AutomationRule | null>(null);

  // Rule form state
  const [ruleName, setRuleName] = useState('');
  const [triggerPanelId, setTriggerPanelId] = useState('');
  const [triggerType, setTriggerType] = useState('on_create');
  const [condField, setCondField] = useState('');
  const [condOp, setCondOp] = useState('equals');
  const [condValue, setCondValue] = useState('');
  const [actionType, setActionType] = useState('create_record');
  const [relationField, setRelationField] = useState('');
  const [updateOp, setUpdateOp] = useState('increment');
  const [updateField, setUpdateField] = useState('');
  const [updateValueFrom, setUpdateValueFrom] = useState('');
  const [fieldMappings, setFieldMappings] = useState<{ target_field: string; source_field: string; default_value: string; mapping_type: string }[]>([]);
  const [fieldVisibility, setFieldVisibility] = useState<{ field: string; visible: boolean; editable: boolean }[]>([]);

  // Target panel fields (for mapping)
  const [targetPanelFields, setTargetPanelFields] = useState<{ key: string; label: string }[]>([]);
  const [loadingTargetFields, setLoadingTargetFields] = useState(false);

  // Logs
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);

  const getHeaders = useCallback(async () => {
    const token = await getIdToken();
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }, [getIdToken]);

  const fetchData = useCallback(async () => {
    const hdrs = await getHeaders();
    setLoading(true);
    try {
      const [panelsRes, rulesRes] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/panels`, { headers: hdrs }),
        fetch(`${API_URL}/api/business-tools/automation/rules`, { headers: hdrs }),
      ]);
      if (panelsRes.ok) {
        const d = await panelsRes.json();
        setPanels(d.panels || []);
      }
      if (rulesRes.ok) {
        const d = await rulesRes.json();
        setRules(d.rules || []);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [getHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Derived data
  const triggerPanel = panels.find(p => p.id === triggerPanelId);
  const triggerFields = triggerPanel?.fields || [];
  const dataFields = triggerFields.filter(f => f.type !== 'relation');
  const relationFields = triggerFields.filter(f => f.type === 'relation');

  const condFieldInfo = dataFields.find(f => f.key === condField);
  const condFieldHasOptions = condFieldInfo && (condFieldInfo.type === 'dropdown' || condFieldInfo.type === 'multiselect') && condFieldInfo.options?.length;

  // Derive target panel from relation field
  const selectedRelField = triggerFields.find(f => f.key === relationField);
  const derivedTargetId = selectedRelField?.relatedPanel || '';
  const derivedTargetType = SYSTEM_MODULES.includes(derivedTargetId) ? 'system' : 'custom';
  const derivedTargetName = SYSTEM_MODULES.includes(derivedTargetId)
    ? MODULE_LABELS[derivedTargetId] || derivedTargetId
    : panels.find(p => p.id === derivedTargetId)?.name || derivedTargetId;

  // Source fields for mapping (includes invoice line item fields)
  const sourceFieldsForMapping = [
    ...dataFields.map(f => ({ key: f.key, label: f.label })),
    ...relationFields.map(f => ({ key: f.key, label: f.label })),
    // Special reference fields
    { key: '_parent_id', label: 'Source Record ID (reference)' },
  ];

  // Fetch target panel fields when relation changes
  const fetchTargetFields = useCallback(async (moduleId: string) => {
    if (!moduleId) { setTargetPanelFields([]); return; }
    setLoadingTargetFields(true);
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/panels/module-fields/${moduleId}`, { headers: hdrs });
      if (res.ok) {
        const d = await res.json();
        setTargetPanelFields(d.fields || []);
      }
    } catch { /* ignore */ }
    setLoadingTargetFields(false);
  }, [getHeaders]);

  useEffect(() => {
    if (derivedTargetId && actionType !== 'update_record') {
      fetchTargetFields(derivedTargetId);
    }
  }, [derivedTargetId, actionType, fetchTargetFields]);

  // Reset form
  const resetForm = () => {
    setRuleName(''); setTriggerPanelId(''); setTriggerType('on_create');
    setCondField(''); setCondOp('equals'); setCondValue('');
    setActionType('create_record'); setRelationField('');
    setUpdateOp('increment'); setUpdateField(''); setUpdateValueFrom('');
    setFieldMappings([]); setFieldVisibility([]);
    setTargetPanelFields([]);
  };

  const openCreate = () => { resetForm(); setEditingRule(null); setShowModal(true); };

  const openEdit = (rule: AutomationRule) => {
    setEditingRule(rule);
    setRuleName(rule.name);
    setTriggerPanelId(rule.trigger_panel_id);
    setTriggerType(rule.trigger_type || 'on_create');
    setCondField(rule.condition?.field || '');
    setCondOp(rule.condition?.operator || 'equals');
    setCondValue(rule.condition?.value || '');
    setActionType(rule.action_type || 'create_record');
    setRelationField(rule.relation_field || '');
    setUpdateOp(rule.update_operation || 'increment');
    setUpdateField(rule.update_field || '');
    setUpdateValueFrom(rule.update_value_from || '');
    setFieldMappings((rule.field_mappings || []).map(fm => ({
      target_field: fm.target_field,
      source_field: fm.source_field || '',
      default_value: fm.default_value || '',
      mapping_type: fm.mapping_type || 'field',
    })));
    setFieldVisibility(rule.field_visibility || []);
    setShowModal(true);
  };

  // Auto-map matching fields
  const handleSelectAll = () => {
    if (!targetPanelFields.length) return;
    const mapped = targetPanelFields.map(tf => {
      const matchSource = sourceFieldsForMapping.find(
        sf => sf.key === tf.key || sf.label.toLowerCase() === tf.label.toLowerCase()
      );
      return {
        target_field: tf.key,
        source_field: matchSource?.key || '',
        default_value: '',
        mapping_type: matchSource ? 'field' : 'default',
      };
    });
    setFieldMappings(mapped);
  };

  // Add empty mapping row
  const addMappingRow = () => {
    setFieldMappings(prev => [...prev, { target_field: '', source_field: '', default_value: '', mapping_type: 'field' }]);
  };

  const removeMappingRow = (idx: number) => {
    setFieldMappings(prev => prev.filter((_, i) => i !== idx));
  };

  const updateMapping = (idx: number, field: string, value: string) => {
    setFieldMappings(prev => prev.map((m, i) => i === idx ? { ...m, [field]: value } : m));
  };

  // Save rule
  const handleSave = async () => {
    if (!ruleName.trim()) { toast.error('Rule name is required'); return; }
    if (!triggerPanelId) { toast.error('Select a trigger panel'); return; }
    if (!relationField) { toast.error('Select a relation field'); return; }
    if (!derivedTargetId) { toast.error('Relation field has no linked target'); return; }

    if (triggerType === 'condition_based' && !condField) {
      toast.error('Condition field is required for condition-based trigger');
      return;
    }

    if (actionType === 'update_record') {
      if (!updateField) { toast.error('Select target field for update'); return; }
      if (!updateValueFrom) { toast.error('Select value source field'); return; }
    }

    if ((actionType === 'create_record' || actionType === 'create_records_per_item') && fieldMappings.length === 0) {
      toast.error('Add at least one field mapping');
      return;
    }

    setSaving(true);
    const body: any = {
      name: ruleName.trim(),
      trigger_panel_id: triggerPanelId,
      trigger_type: triggerType,
      action_type: actionType,
      target_panel_id: derivedTargetId,
      relation_field: relationField,
    };

    if (condField) {
      body.condition = { field: condField, operator: condOp, value: condValue || undefined };
    }

    if (actionType === 'update_record') {
      body.update_operation = updateOp;
      body.update_field = updateField;
      body.update_value_from = updateValueFrom;
    }

    if (actionType === 'create_record' || actionType === 'create_records_per_item') {
      body.field_mappings = fieldMappings.filter(fm => fm.target_field);
      body.field_visibility = fieldVisibility;
    }

    try {
      const hdrs = await getHeaders();
      const url = editingRule
        ? `${API_URL}/api/business-tools/automation/rules/${editingRule.id}`
        : `${API_URL}/api/business-tools/automation/rules`;
      const res = await fetch(url, {
        method: editingRule ? 'PUT' : 'POST',
        headers: hdrs,
        body: JSON.stringify(body),
      });
      if (res.ok) {
        toast.success(editingRule ? 'Rule updated' : 'Rule created');
        setShowModal(false);
        fetchData();
      } else {
        const d = await res.json().catch(() => ({ detail: 'Failed' }));
        toast.error(d.detail || 'Failed to save rule');
      }
    } catch { toast.error('Network error'); }
    setSaving(false);
  };

  const deleteRule = async (id: string) => {
    if (!confirm('Delete this rule?')) return;
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${id}`, { method: 'DELETE', headers: hdrs });
      if (res.ok) { toast.success('Rule deleted'); fetchData(); }
      else { toast.error('Failed to delete'); }
    } catch { toast.error('Network error'); }
  };

  const toggleRule = async (rule: AutomationRule) => {
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${rule.id}`, {
        method: 'PUT', headers: hdrs,
        body: JSON.stringify({ is_active: !rule.is_active }),
      });
      if (res.ok) { toast.success(rule.is_active ? 'Rule disabled' : 'Rule enabled'); fetchData(); }
    } catch { toast.error('Network error'); }
  };

  const fetchLogs = async () => {
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/logs`, { headers: hdrs });
      if (res.ok) {
        const d = await res.json();
        setLogs(d.logs || []);
      }
    } catch { /* ignore */ }
    setShowLogs(true);
  };

  // System target fields for update_record
  const SYSTEM_TARGET_FIELDS: Record<string, { key: string; label: string }[]> = {
    inventory: [
      { key: 'stock', label: 'Stock' },
      { key: 'quantity', label: 'Quantity' },
      { key: 'minStock', label: 'Min Stock' },
      { key: 'reorderPoint', label: 'Reorder Point' },
    ],
  };

  const updateTargetFields = (() => {
    if (!derivedTargetId) return [];
    if (derivedTargetType === 'system') return SYSTEM_TARGET_FIELDS[derivedTargetId] || [];
    const tp = panels.find(p => p.id === derivedTargetId);
    return (tp?.fields || []).filter(f => f.type !== 'relation').map(f => ({ key: f.key, label: f.label }));
  })();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="automation-loading">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto" data-testid="automation-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Zap className="h-6 w-6 text-amber-500" /> Automation Rules
          </h1>
          <p className="text-sm text-gray-500 mt-1">Create IF-THEN rules to automate workflows between panels</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchLogs} className="flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50" data-testid="view-logs-btn">
            <Activity className="h-4 w-4" /> Logs
          </button>
          <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600" data-testid="create-rule-btn">
            <Plus className="h-4 w-4" /> New Rule
          </button>
        </div>
      </div>

      {/* Warning */}
      {panels.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3 mb-6" data-testid="no-panels-warning">
          <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
          <div>
            <p className="font-medium text-amber-800">No Custom Panels Found</p>
            <p className="text-sm text-amber-600 mt-1">Create panels with relation fields first, then build automation rules.</p>
          </div>
        </div>
      )}

      {/* Rules list */}
      <div className="space-y-3" data-testid="rules-list">
        {rules.length === 0 && panels.length > 0 && (
          <div className="text-center py-12 text-gray-500">
            <Zap className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="font-medium">No automation rules yet</p>
            <p className="text-sm mt-1">Create your first rule to automate workflows</p>
          </div>
        )}

        {rules.map(rule => (
          <div key={rule.id} className={`p-4 rounded-lg border transition-colors ${rule.is_active ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200 opacity-70'}`} data-testid={`rule-${rule.id}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Zap className={`h-4 w-4 ${rule.is_active ? 'text-amber-500' : 'text-gray-400'}`} />
                  <span className="font-semibold text-gray-900">{rule.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${rule.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                    {rule.is_active ? 'Active' : 'Disabled'}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                    {TRIGGER_TYPES.find(t => t.value === rule.trigger_type)?.label || rule.trigger_type}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                    {ACTION_TYPES.find(a => a.value === rule.action_type)?.label || rule.action_type}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  <span className="text-amber-600 font-medium">{rule.trigger_panel_name}</span>
                  <ChevronRight className="h-3 w-3 inline mx-1" />
                  <span className="text-green-600 font-medium">{rule.target_panel_name || 'System'}</span>
                  {rule.execution_count > 0 && (
                    <span className="ml-3 text-xs text-gray-400">Executed {rule.execution_count}x</span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-1 ml-3">
                <button onClick={() => toggleRule(rule)} className="p-1.5 rounded-lg hover:bg-gray-100" title={rule.is_active ? 'Disable' : 'Enable'} data-testid={`toggle-rule-${rule.id}`}>
                  {rule.is_active ? <Power className="h-4 w-4 text-green-600" /> : <PowerOff className="h-4 w-4 text-gray-400" />}
                </button>
                <button onClick={() => openEdit(rule)} className="p-1.5 rounded-lg hover:bg-gray-100" data-testid={`edit-rule-${rule.id}`}>
                  <Pencil className="h-4 w-4 text-gray-500" />
                </button>
                <button onClick={() => deleteRule(rule.id)} className="p-1.5 rounded-lg hover:bg-red-50" data-testid={`delete-rule-${rule.id}`}>
                  <Trash2 className="h-4 w-4 text-red-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ═══ CREATE/EDIT MODAL ═══ */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-y-auto" data-testid="rule-modal">
          <div className="bg-white rounded-xl w-full max-w-2xl mt-8 mb-8 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-bold">{editingRule ? 'Edit' : 'Create'} Automation Rule</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded" data-testid="close-modal"><X className="h-5 w-5" /></button>
            </div>
            <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto">

              {/* Rule Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name *</label>
                <input type="text" value={ruleName} onChange={e => setRuleName(e.target.value)}
                  placeholder="e.g. Invoice → QC Records" className="w-full px-3 py-2 border rounded-lg text-sm" data-testid="rule-name-input" />
              </div>

              {/* WHEN (Trigger) */}
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 space-y-3">
                <label className="block text-sm font-semibold text-amber-800">WHEN (Trigger)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Source Panel *</label>
                    <select value={triggerPanelId} onChange={e => { setTriggerPanelId(e.target.value); setRelationField(''); setCondField(''); setFieldMappings([]); }}
                      className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="trigger-panel-select">
                      <option value="">Select panel...</option>
                      {panels.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Trigger Type *</label>
                    <select value={triggerType} onChange={e => setTriggerType(e.target.value)}
                      className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="trigger-type-select">
                      {TRIGGER_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* IF (Condition) — shown for condition_based or optional */}
              {triggerPanelId && (
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200 space-y-3">
                  <label className="block text-sm font-semibold text-yellow-800">
                    IF (Condition) {triggerType !== 'condition_based' && <span className="text-xs font-normal text-yellow-600">— optional</span>}
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <select value={condField} onChange={e => { setCondField(e.target.value); setCondValue(''); }}
                      className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-field-select">
                      <option value="">Field...</option>
                      {dataFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
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

              {/* THEN (Action) */}
              {triggerPanelId && (
                <div className="p-3 bg-green-50 rounded-lg border border-green-200 space-y-3">
                  <label className="block text-sm font-semibold text-green-800">THEN (Action)</label>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Action Type *</label>
                      <select value={actionType} onChange={e => { setActionType(e.target.value); setFieldMappings([]); }}
                        className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="action-type-select">
                        {ACTION_TYPES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Via Relation Field *</label>
                      <select value={relationField} onChange={e => { setRelationField(e.target.value); setFieldMappings([]); setUpdateField(''); }}
                        className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="relation-field-select">
                        <option value="">Select relation...</option>
                        {relationFields.map(f => {
                          const targetLabel = SYSTEM_MODULES.includes(f.relatedPanel || '')
                            ? MODULE_LABELS[f.relatedPanel || ''] || f.relatedPanel
                            : panels.find(p => p.id === f.relatedPanel)?.name || f.relatedPanel;
                          const binding = f.bindingField ? ` via ${f.bindingField}` : '';
                          return <option key={f.key} value={f.key}>{f.label} (→ {targetLabel}{binding})</option>;
                        })}
                      </select>
                    </div>
                  </div>

                  {/* Target panel — auto-derived (read-only) */}
                  {relationField && derivedTargetId && (
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">Target Panel (auto-detected)</label>
                      <div className="w-full px-3 py-2 bg-white border rounded-lg text-sm text-gray-700 flex items-center gap-2" data-testid="target-panel-display">
                        <Lock className="h-3.5 w-3.5 text-gray-400" />
                        <span className="font-medium">{derivedTargetName}</span>
                        <span className="text-xs text-gray-400 ml-auto">{derivedTargetType === 'system' ? 'System Module' : 'Custom Panel'}</span>
                      </div>
                    </div>
                  )}

                  {/* UPDATE RECORD fields */}
                  {actionType === 'update_record' && relationField && derivedTargetId && (
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Operation *</label>
                        <select value={updateOp} onChange={e => setUpdateOp(e.target.value)}
                          className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="update-op-select">
                          {UPDATE_OPS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Target Field *</label>
                        <select value={updateField} onChange={e => setUpdateField(e.target.value)}
                          className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="update-field-select">
                          <option value="">Select field...</option>
                          {updateTargetFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Value From *</label>
                        <select value={updateValueFrom} onChange={e => setUpdateValueFrom(e.target.value)}
                          className="w-full px-2 py-1.5 border rounded-lg text-sm" data-testid="update-value-from-select">
                          <option value="">Select field...</option>
                          {dataFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                        </select>
                      </div>
                    </div>
                  )}

                  {/* FIELD MAPPING for create actions */}
                  {(actionType === 'create_record' || actionType === 'create_records_per_item') && relationField && derivedTargetId && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-gray-700">Field Mapping (Source → Target)</label>
                        <div className="flex items-center gap-2">
                          <button onClick={handleSelectAll} type="button"
                            className="flex items-center gap-1 text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                            data-testid="select-all-btn">
                            <Check className="h-3 w-3" /> Select All
                          </button>
                          <button onClick={addMappingRow} type="button"
                            className="flex items-center gap-1 text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
                            data-testid="add-mapping-btn">
                            <Plus className="h-3 w-3" /> Add Row
                          </button>
                        </div>
                      </div>

                      {loadingTargetFields ? (
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Loader2 className="h-3 w-3 animate-spin" /> Loading target fields...
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {/* Header */}
                          <div className="grid grid-cols-12 gap-2 text-xs font-semibold text-gray-500">
                            <div className="col-span-4">Target Field</div>
                            <div className="col-span-1 text-center">Type</div>
                            <div className="col-span-5">Source / Default Value</div>
                            <div className="col-span-2"></div>
                          </div>

                          {fieldMappings.map((fm, idx) => (
                            <div key={idx} className="grid grid-cols-12 gap-2 items-center" data-testid={`mapping-row-${idx}`}>
                              <select value={fm.target_field} onChange={e => updateMapping(idx, 'target_field', e.target.value)}
                                className="col-span-4 px-2 py-1.5 border rounded text-xs" data-testid={`mapping-target-${idx}`}>
                                <option value="">Target field...</option>
                                {targetPanelFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                              </select>

                              <select value={fm.mapping_type} onChange={e => updateMapping(idx, 'mapping_type', e.target.value)}
                                className="col-span-1 px-1 py-1.5 border rounded text-xs" data-testid={`mapping-type-${idx}`}>
                                <option value="field">Field</option>
                                <option value="default">Default</option>
                                <option value="reference">Ref</option>
                              </select>

                              {fm.mapping_type === 'default' ? (
                                <input type="text" value={fm.default_value} onChange={e => updateMapping(idx, 'default_value', e.target.value)}
                                  placeholder="Default value" className="col-span-5 px-2 py-1.5 border rounded text-xs" data-testid={`mapping-default-${idx}`} />
                              ) : (
                                <select value={fm.source_field} onChange={e => updateMapping(idx, 'source_field', e.target.value)}
                                  className="col-span-5 px-2 py-1.5 border rounded text-xs" data-testid={`mapping-source-${idx}`}>
                                  <option value="">Source field...</option>
                                  {sourceFieldsForMapping.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                                </select>
                              )}

                              <button onClick={() => removeMappingRow(idx)} className="col-span-2 p-1 text-red-400 hover:text-red-600" data-testid={`remove-mapping-${idx}`}>
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          ))}

                          {fieldMappings.length === 0 && (
                            <p className="text-xs text-gray-400 text-center py-2">No mappings yet. Click "Select All" or "Add Row".</p>
                          )}
                        </div>
                      )}

                      {/* Field Visibility */}
                      {fieldMappings.length > 0 && (
                        <div className="mt-3 p-3 bg-gray-50 rounded-lg border">
                          <label className="text-xs font-semibold text-gray-700 mb-2 block">Field Visibility Settings</label>
                          <div className="space-y-1.5">
                            <div className="grid grid-cols-6 gap-2 text-xs font-semibold text-gray-500">
                              <div className="col-span-2">Field</div>
                              <div className="col-span-2 text-center">Visible</div>
                              <div className="col-span-2 text-center">Editable</div>
                            </div>
                            {fieldMappings.filter(fm => fm.target_field).map((fm, idx) => {
                              const vis = fieldVisibility.find(v => v.field === fm.target_field) || { field: fm.target_field, visible: true, editable: true };
                              const tfLabel = targetPanelFields.find(f => f.key === fm.target_field)?.label || fm.target_field;
                              return (
                                <div key={idx} className="grid grid-cols-6 gap-2 items-center text-xs">
                                  <div className="col-span-2 text-gray-700">{tfLabel}</div>
                                  <div className="col-span-2 text-center">
                                    <input type="checkbox" checked={vis.visible}
                                      onChange={e => {
                                        const newVis = fieldVisibility.filter(v => v.field !== fm.target_field);
                                        newVis.push({ field: fm.target_field, visible: e.target.checked, editable: vis.editable });
                                        setFieldVisibility(newVis);
                                      }}
                                      className="rounded border-gray-300 text-green-600" data-testid={`vis-visible-${fm.target_field}`} />
                                  </div>
                                  <div className="col-span-2 text-center">
                                    <input type="checkbox" checked={vis.editable}
                                      onChange={e => {
                                        const newVis = fieldVisibility.filter(v => v.field !== fm.target_field);
                                        newVis.push({ field: fm.target_field, visible: vis.visible, editable: e.target.checked });
                                        setFieldVisibility(newVis);
                                      }}
                                      className="rounded border-gray-300 text-blue-600" data-testid={`vis-editable-${fm.target_field}`} />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50" data-testid="cancel-btn">Cancel</button>
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50"
                data-testid="save-rule-btn">
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                {editingRule ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ LOGS MODAL ═══ */}
      {showLogs && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-y-auto" data-testid="logs-modal">
          <div className="bg-white rounded-xl w-full max-w-3xl mt-8 mb-8 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-bold flex items-center gap-2"><Activity className="h-5 w-5" /> Execution Logs</h2>
              <button onClick={() => setShowLogs(false)} className="p-1 hover:bg-gray-100 rounded"><X className="h-5 w-5" /></button>
            </div>
            <div className="p-4 max-h-[60vh] overflow-y-auto">
              {logs.length === 0 ? (
                <p className="text-center text-gray-500 py-8">No execution logs yet</p>
              ) : (
                <div className="space-y-2">
                  {logs.map((log, idx) => (
                    <div key={idx} className={`p-3 rounded-lg border text-xs ${log.status === 'success' ? 'bg-green-50 border-green-200' : log.status === 'error' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'}`}>
                      <div className="flex items-center justify-between">
                        <span className="font-semibold">{log.ruleName}</span>
                        <span className={`px-2 py-0.5 rounded-full ${log.status === 'success' ? 'bg-green-200 text-green-800' : log.status === 'error' ? 'bg-red-200 text-red-800' : 'bg-yellow-200 text-yellow-800'}`}>
                          {log.status}
                        </span>
                      </div>
                      <p className="text-gray-600 mt-1">{log.message || log.error || ''}</p>
                      <p className="text-gray-400 mt-1">{log.action_type} | {log.event} | {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
