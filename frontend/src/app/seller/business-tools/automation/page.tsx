'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import {
  Zap, Plus, Pencil, Trash2, Loader2, X, Save, Power, PowerOff,
  ChevronRight, Activity, AlertTriangle, Check, Target, ArrowRight
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// ── Constants matching backend contract ──

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

const DATA_MODES = [
  { value: 'smart_sync', label: 'Smart Sync', desc: 'Auto-map matching fields + explicit mappings' },
  { value: 'manual_only', label: 'Manual Only', desc: 'Only explicitly mapped fields transfer' },
  { value: 'full_copy', label: 'Full Copy', desc: 'All matching target fields copied from source' },
];

const SYSTEM_MODULES = [
  { id: 'inventory', label: 'Inventory' },
  { id: 'invoices', label: 'Invoices' },
  { id: 'buyers', label: 'Buyers' },
  { id: 'suppliers', label: 'Suppliers' },
  { id: 'purchase_orders', label: 'Purchase Orders' },
  { id: 'quotations', label: 'Quotations' },
  { id: 'composite_products', label: 'Composite Products' },
  { id: 'employees', label: 'Employees' },
];

const SYSTEM_MODULE_IDS = new Set(SYSTEM_MODULES.map(m => m.id));

// ── Types matching backend Pydantic models ──

interface PanelField {
  key: string;
  label: string;
  type: string;
  relatedPanel?: string | null;
  options?: string[];
  systemManaged?: boolean;
  bindingField?: string;
}

interface Panel {
  id: string;
  name: string;
  fields: PanelField[];
}

interface FieldMappingForm {
  target_field: string;
  source_field: string;
  default_value: string;
  mapping_type: 'field' | 'default' | 'reference';
}

interface FieldVisibilityForm {
  field: string;
  visible: boolean;
  editable: boolean;
}

interface TargetForm {
  target_panel_id: string;
  action_type: string;
  data_mode: string;
  relation_field: string;
  // For update_record — MATCH + UPDATE
  match_target_field: string;
  match_source_field: string;
  update_operation: string;
  update_field: string;
  update_value_from: string;
  field_mappings: FieldMappingForm[];
  field_visibility: FieldVisibilityForm[];
  // UI-only state
  _targetFields: { key: string; label: string }[];
  _loadingFields: boolean;
}

interface RuleForm {
  name: string;
  trigger_panel_id: string;
  trigger_type: string;
  condition: { field: string; operator: string; value: string };
  targets: TargetForm[];
}

interface RuleResponse {
  id: string;
  name: string;
  trigger_panel_id: string;
  trigger_panel_name?: string;
  trigger_type: string;
  condition?: { field: string; operator: string; value?: string } | null;
  targets: {
    target_panel_id: string;
    target_panel_name?: string;
    action_type: string;
    data_mode?: string;
    relation_field?: string | null;
    match_target_field?: string | null;
    match_source_field?: string | null;
    update_operation?: string | null;
    update_field?: string | null;
    update_value_from?: string | null;
    field_mappings?: { target_field: string; source_field?: string; default_value?: string; mapping_type: string }[] | null;
    field_visibility?: { field: string; visible: boolean; editable: boolean }[] | null;
  }[];
  is_active: boolean;
  execution_count: number;
  last_executed?: string | null;
  priority: number;
}

// ── Helper: create empty target ──

function createEmptyTarget(): TargetForm {
  return {
    target_panel_id: '',
    action_type: 'create_record',
    data_mode: 'smart_sync',
    relation_field: '',
    match_target_field: '',
    match_source_field: '',
    update_operation: 'increment',
    update_field: '',
    update_value_from: '',
    field_mappings: [],
    field_visibility: [],
    _targetFields: [],
    _loadingFields: false,
  };
}

function createEmptyRule(): RuleForm {
  return {
    name: '',
    trigger_panel_id: '',
    trigger_type: 'on_create',
    condition: { field: '', operator: 'equals', value: '' },
    targets: [],
  };
}

// ── Utility: get panel/module name ──

function getTargetName(id: string, panels: Panel[]): string {
  const sys = SYSTEM_MODULES.find(m => m.id === id);
  if (sys) return sys.label;
  const p = panels.find(p => p.id === id);
  return p?.name || id;
}

// ══════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════

export default function AutomationPage() {
  const { getIdToken } = useAuth();
  const [panels, setPanels] = useState<Panel[]>([]);
  const [rules, setRules] = useState<RuleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  // Rule form — single state object
  const [rule, setRule] = useState<RuleForm>(createEmptyRule());

  // Logs
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);

  // Preview
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // System module source fields (when a system module is selected as trigger)
  const [systemSourceFields, setSystemSourceFields] = useState<PanelField[]>([]);

  const getHeaders = useCallback(async () => {
    const token = await getIdToken();
    return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  }, [getIdToken]);

  // ── Data Fetching ──

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const hdrs = await getHeaders();
      const [panelsRes, rulesRes] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/panels`, { headers: hdrs }),
        fetch(`${API_URL}/api/business-tools/automation/rules`, { headers: hdrs }),
      ]);
      if (panelsRes.ok) setPanels((await panelsRes.json()).panels || []);
      if (rulesRes.ok) setRules((await rulesRes.json()).rules || []);
    } catch { /* silent */ }
    setLoading(false);
  }, [getHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Fetch source fields when trigger panel is a system module ──
  useEffect(() => {
    if (!rule.trigger_panel_id) { setSystemSourceFields([]); return; }
    if (!SYSTEM_MODULE_IDS.has(rule.trigger_panel_id)) { setSystemSourceFields([]); return; }
    (async () => {
      try {
        const hdrs = await getHeaders();
        const res = await fetch(`${API_URL}/api/business-tools/panels/module-fields/${rule.trigger_panel_id}`, { headers: hdrs });
        if (res.ok) {
          const d = await res.json();
          setSystemSourceFields(d.fields || []);
        }
      } catch { setSystemSourceFields([]); }
    })();
  }, [rule.trigger_panel_id, getHeaders]);

  // ── Fetch target fields for a specific target index ──

  const fetchTargetFields = useCallback(async (targetIdx: number, panelId: string) => {
    if (!panelId) return;
    setRule(prev => {
      const targets = [...prev.targets];
      targets[targetIdx] = { ...targets[targetIdx], _loadingFields: true };
      return { ...prev, targets };
    });
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/panels/module-fields/${panelId}`, { headers: hdrs });
      if (res.ok) {
        const d = await res.json();
        setRule(prev => {
          const targets = [...prev.targets];
          targets[targetIdx] = {
            ...targets[targetIdx],
            _targetFields: d.fields || [],
            _loadingFields: false,
          };
          return { ...prev, targets };
        });
      }
    } catch {
      setRule(prev => {
        const targets = [...prev.targets];
        targets[targetIdx] = { ...targets[targetIdx], _loadingFields: false };
        return { ...prev, targets };
      });
    }
  }, [getHeaders]);

  // ── Derived: source panel fields ──

  const isSystemSource = SYSTEM_MODULE_IDS.has(rule.trigger_panel_id);
  const sourcePanel = isSystemSource ? null : panels.find(p => p.id === rule.trigger_panel_id);
  const sourceFields: PanelField[] = isSystemSource ? systemSourceFields : (sourcePanel?.fields || []);
  const sourceDataFields = sourceFields.filter(f => f.type !== 'relation');
  const sourceRelationFields = sourceFields.filter(f => f.type === 'relation');
  const sourceAllFields = sourceFields; // ALL source fields for lookup key

  // Source fields available for mapping (data + relations + special refs)
  const sourceFieldsForMapping = [
    ...sourceDataFields.map(f => ({ key: f.key, label: f.label })),
    ...sourceRelationFields.map(f => ({ key: f.key, label: f.label })),
    { key: '_parent_id', label: 'Source Record ID (reference)' },
  ];

  // All available target panels (custom + system)
  const allTargetOptions = [
    ...panels.map(p => ({ id: p.id, label: p.name, type: 'panel' as const })),
    ...SYSTEM_MODULES.map(m => ({ id: m.id, label: m.label, type: 'system' as const })),
  ];

  // All available source panels (custom + system)
  const allSourceOptions = [
    ...panels.map(p => ({ id: p.id, label: p.name, type: 'panel' as const })),
    ...SYSTEM_MODULES.map(m => ({ id: m.id, label: m.label, type: 'system' as const })),
  ];

  // Condition field info
  const condFieldInfo = sourceDataFields.find(f => f.key === rule.condition.field);
  const condHasOptions = condFieldInfo && (condFieldInfo.type === 'dropdown' || condFieldInfo.type === 'multiselect') && condFieldInfo.options?.length;

  // ── State Mutations ──

  const updateRule = (patch: Partial<RuleForm>) => setRule(prev => ({ ...prev, ...patch }));

  const updateCondition = (patch: Partial<RuleForm['condition']>) =>
    setRule(prev => ({ ...prev, condition: { ...prev.condition, ...patch } }));

  const addTarget = () => setRule(prev => ({
    ...prev,
    targets: [...prev.targets, createEmptyTarget()],
  }));

  const removeTarget = (idx: number) => setRule(prev => ({
    ...prev,
    targets: prev.targets.filter((_, i) => i !== idx),
  }));

  const updateTarget = (idx: number, patch: Partial<TargetForm>) => {
    setRule(prev => {
      const targets = [...prev.targets];
      targets[idx] = { ...targets[idx], ...patch };
      return { ...prev, targets };
    });
  };

  const updateTargetMapping = (tIdx: number, mIdx: number, patch: Partial<FieldMappingForm>) => {
    setRule(prev => {
      const targets = [...prev.targets];
      const mappings = [...targets[tIdx].field_mappings];
      mappings[mIdx] = { ...mappings[mIdx], ...patch };
      targets[tIdx] = { ...targets[tIdx], field_mappings: mappings };
      return { ...prev, targets };
    });
  };

  const addMappingRow = (tIdx: number) => {
    setRule(prev => {
      const targets = [...prev.targets];
      targets[tIdx] = {
        ...targets[tIdx],
        field_mappings: [...targets[tIdx].field_mappings, { target_field: '', source_field: '', default_value: '', mapping_type: 'field' }],
      };
      return { ...prev, targets };
    });
  };

  const removeMappingRow = (tIdx: number, mIdx: number) => {
    setRule(prev => {
      const targets = [...prev.targets];
      targets[tIdx] = {
        ...targets[tIdx],
        field_mappings: targets[tIdx].field_mappings.filter((_, i) => i !== mIdx),
      };
      return { ...prev, targets };
    });
  };

  const selectAllMappings = (tIdx: number) => {
    const target = rule.targets[tIdx];
    if (!target._targetFields.length) return;
    const mapped: FieldMappingForm[] = target._targetFields.map(tf => {
      const match = sourceFieldsForMapping.find(
        sf => sf.key === tf.key || sf.label.toLowerCase() === tf.label.toLowerCase()
      );
      return {
        target_field: tf.key,
        source_field: match?.key || '',
        default_value: '',
        mapping_type: match ? 'field' : 'default',
      };
    });
    updateTarget(tIdx, { field_mappings: mapped });
  };

  const toggleVisibility = (tIdx: number, fieldKey: string, prop: 'visible' | 'editable', val: boolean) => {
    setRule(prev => {
      const targets = [...prev.targets];
      const vis = [...targets[tIdx].field_visibility];
      const existing = vis.findIndex(v => v.field === fieldKey);
      if (existing >= 0) {
        vis[existing] = { ...vis[existing], [prop]: val };
      } else {
        vis.push({ field: fieldKey, visible: prop === 'visible' ? val : true, editable: prop === 'editable' ? val : true });
      }
      targets[tIdx] = { ...targets[tIdx], field_visibility: vis };
      return { ...prev, targets };
    });
  };

  const getVisibility = (tIdx: number, fieldKey: string) => {
    return rule.targets[tIdx].field_visibility.find(v => v.field === fieldKey) || { field: fieldKey, visible: true, editable: true };
  };

  // ── Target panel change handler ──

  const handleTargetPanelChange = (tIdx: number, panelId: string) => {
    // Auto-detect: if source has a relation field pointing to this target, pre-select it as match
    let autoMatchSource = '';
    let autoMatchTarget = '';
    if (panelId) {
      const matchingRelation = sourceFields.find(f =>
        f.type === 'relation' && (
          f.relatedPanel === panelId ||
          f.relatedPanel === panelId.toLowerCase() ||
          (panelId === 'inventory' && f.relatedPanel === 'inventory') ||
          (panelId === 'purchase_orders' && f.relatedPanel === 'purchase_orders') ||
          (panelId === 'employees' && f.relatedPanel === 'employees') ||
          (panelId === 'buyers' && f.relatedPanel === 'buyers') ||
          (panelId === 'suppliers' && f.relatedPanel === 'suppliers')
        )
      );
      if (matchingRelation) {
        autoMatchSource = matchingRelation.key;
        autoMatchTarget = matchingRelation.key; // same field name in target
      }
    }

    updateTarget(tIdx, {
      target_panel_id: panelId,
      relation_field: autoMatchSource,
      match_source_field: autoMatchSource,
      match_target_field: autoMatchTarget,
      field_mappings: [],
      field_visibility: [],
      update_field: '',
      _targetFields: [],
    });
    if (panelId) fetchTargetFields(tIdx, panelId);
  };

  // ── Modal open/close ──

  const openCreate = () => {
    setRule(createEmptyRule());
    setEditingRuleId(null);
    setShowModal(true);
  };

  const openEdit = (r: RuleResponse) => {
    setEditingRuleId(r.id);
    setRule({
      name: r.name,
      trigger_panel_id: r.trigger_panel_id,
      trigger_type: r.trigger_type,
      condition: r.condition ? { field: r.condition.field || '', operator: r.condition.operator || 'equals', value: r.condition.value || '' } : { field: '', operator: 'equals', value: '' },
      targets: (r.targets || []).map(t => ({
        target_panel_id: t.target_panel_id,
        action_type: t.action_type || 'create_record',
        data_mode: t.data_mode || 'smart_sync',
        relation_field: t.relation_field || '',
        match_target_field: t.match_target_field || '',
        match_source_field: t.match_source_field || t.relation_field || '',
        update_operation: t.update_operation || 'increment',
        update_field: t.update_field || '',
        update_value_from: t.update_value_from || '',
        field_mappings: (t.field_mappings || []).map(fm => ({
          target_field: fm.target_field,
          source_field: fm.source_field || '',
          default_value: fm.default_value || '',
          mapping_type: (fm.mapping_type || 'field') as 'field' | 'default' | 'reference',
        })),
        field_visibility: (t.field_visibility || []).map(fv => ({
          field: fv.field,
          visible: fv.visible,
          editable: fv.editable,
        })),
        _targetFields: [],
        _loadingFields: false,
      })),
    });
    setShowModal(true);
    // Fetch target fields for each target
    (r.targets || []).forEach((t, idx) => {
      if (t.target_panel_id) fetchTargetFields(idx, t.target_panel_id);
    });
  };

  // ── PAYLOAD BUILDER & SUBMIT ──

  const handleSave = async () => {
    // Validation
    if (!rule.name.trim()) { toast.error('Rule name is required'); return; }
    if (!rule.trigger_panel_id) { toast.error('Select a source panel'); return; }
    if (rule.targets.length === 0) { toast.error('Add at least one target'); return; }

    if (rule.trigger_type === 'condition_based' && !rule.condition.field) {
      toast.error('Condition field is required for condition-based trigger');
      return;
    }

    for (let i = 0; i < rule.targets.length; i++) {
      const t = rule.targets[i];
      if (!t.target_panel_id) { toast.error(`Target ${i + 1}: Select a target panel`); return; }
      if (t.action_type === 'update_record') {
        if (!t.match_target_field) { toast.error(`Target ${i + 1}: Select a Target Field in Match Condition`); return; }
        if (!t.match_source_field) { toast.error(`Target ${i + 1}: Select a Source Field in Match Condition`); return; }
        if (!t.update_field) { toast.error(`Target ${i + 1}: Select target field for update`); return; }
        if (!t.update_value_from) { toast.error(`Target ${i + 1}: Select value source field`); return; }
      }
      if (t.action_type === 'create_record' || t.action_type === 'create_records_per_item') {
        if (t.data_mode === 'manual_only' && t.field_mappings.filter(fm => fm.target_field).length === 0) {
          toast.error(`Target ${i + 1}: Manual Only mode requires at least one field mapping`);
          return;
        }
      }
    }

    // Build payload matching backend contract EXACTLY
    const payload: any = {
      name: rule.name.trim(),
      trigger_panel_id: rule.trigger_panel_id,
      trigger_type: rule.trigger_type,
      targets: rule.targets.map(t => {
        const target: any = {
          target_panel_id: t.target_panel_id,
          action_type: t.action_type,
          data_mode: t.data_mode,
        };
        if (t.relation_field) target.relation_field = t.relation_field;
        if (t.action_type === 'update_record') {
          target.match_target_field = t.match_target_field;
          target.match_source_field = t.match_source_field;
          target.update_operation = t.update_operation;
          target.update_field = t.update_field;
          target.update_value_from = t.update_value_from;
        }
        if (t.action_type === 'create_record' || t.action_type === 'create_records_per_item') {
          target.field_mappings = t.field_mappings.filter(fm => fm.target_field).map(fm => ({
            target_field: fm.target_field,
            source_field: fm.mapping_type === 'field' || fm.mapping_type === 'reference' ? fm.source_field || undefined : undefined,
            default_value: fm.mapping_type === 'default' ? fm.default_value || undefined : undefined,
            mapping_type: fm.mapping_type,
          }));
          target.field_visibility = t.field_visibility;
        }
        return target;
      }),
    };

    if (rule.condition.field) {
      payload.condition = {
        field: rule.condition.field,
        operator: rule.condition.operator,
        value: rule.condition.value || undefined,
      };
    }

    console.log('FINAL PAYLOAD', JSON.stringify(payload, null, 2));

    setSaving(true);
    try {
      const hdrs = await getHeaders();
      const url = editingRuleId
        ? `${API_URL}/api/business-tools/automation/rules/${editingRuleId}`
        : `${API_URL}/api/business-tools/automation/rules`;
      const res = await fetch(url, {
        method: editingRuleId ? 'PUT' : 'POST',
        headers: hdrs,
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        toast.success(editingRuleId ? 'Rule updated' : 'Rule created');
        setShowModal(false);
        fetchData();
      } else {
        const d = await res.json().catch(() => ({ detail: 'Failed' }));
        toast.error(d.detail || 'Failed to save rule');
      }
    } catch { toast.error('Network error'); }
    setSaving(false);
  };

  // ── Delete / Toggle ──

  const deleteRule = async (id: string) => {
    if (!confirm('Delete this rule?')) return;
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${id}`, { method: 'DELETE', headers: hdrs });
      if (res.ok) { toast.success('Rule deleted'); fetchData(); }
      else { toast.error('Failed to delete'); }
    } catch { toast.error('Network error'); }
  };

  const toggleRule = async (r: RuleResponse) => {
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/rules/${r.id}`, {
        method: 'PUT', headers: hdrs,
        body: JSON.stringify({ is_active: !r.is_active }),
      });
      if (res.ok) { toast.success(r.is_active ? 'Rule disabled' : 'Rule enabled'); fetchData(); }
    } catch { toast.error('Network error'); }
  };

  const fetchLogs = async () => {
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/logs`, { headers: hdrs });
      if (res.ok) setLogs((await res.json()).logs || []);
    } catch { /* silent */ }
    setShowLogs(true);
  };

  // ── Preview Data ──
  const fetchPreview = async () => {
    if (!rule.trigger_panel_id || rule.targets.length === 0) {
      toast.error('Set source panel and at least one target to preview');
      return;
    }
    setLoadingPreview(true);
    setPreviewData(null);
    try {
      const hdrs = await getHeaders();
      const res = await fetch(`${API_URL}/api/business-tools/automation/preview`, {
        method: 'POST',
        headers: hdrs,
        body: JSON.stringify({
          trigger_panel_id: rule.trigger_panel_id,
          targets: rule.targets.map(t => ({
            target_panel_id: t.target_panel_id,
            action_type: t.action_type,
            data_mode: t.data_mode,
            relation_field: t.relation_field || undefined,
            match_target_field: t.match_target_field || undefined,
            match_source_field: t.match_source_field || undefined,
            update_operation: t.update_operation || undefined,
            update_field: t.update_field || undefined,
            update_value_from: t.update_value_from || undefined,
            field_mappings: t.field_mappings.filter(fm => fm.target_field).map(fm => ({
              target_field: fm.target_field,
              source_field: fm.source_field || undefined,
              default_value: fm.default_value || undefined,
              mapping_type: fm.mapping_type,
            })),
          })),
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setPreviewData(d.previews || []);
        if (d.message) toast.info(d.message);
      } else {
        toast.error('Preview failed');
      }
    } catch { toast.error('Preview failed'); }
    setLoadingPreview(false);
  };


  // ── System target fields for update_record ──

  const SYSTEM_UPDATE_FIELDS: Record<string, { key: string; label: string }[]> = {
    inventory: [
      { key: 'stock', label: 'Stock' },
      { key: 'quantity', label: 'Quantity' },
      { key: 'minStock', label: 'Min Stock' },
      { key: 'reorderPoint', label: 'Reorder Point' },
    ],
  };

  const getUpdateFields = (targetPanelId: string, targetFields: { key: string; label: string }[]) => {
    if (SYSTEM_MODULE_IDS.has(targetPanelId)) return SYSTEM_UPDATE_FIELDS[targetPanelId] || [];
    return targetFields;
  };

  // ══════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="automation-loading">
        <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
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
          <p className="text-sm text-gray-500 mt-1">Create rules: 1 source panel triggers actions on multiple target panels</p>
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

      {/* Warning: no panels */}
      {panels.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3 mb-6" data-testid="no-panels-warning">
          <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
          <div>
            <p className="font-medium text-amber-800">No Custom Panels Found</p>
            <p className="text-sm text-amber-600 mt-1">You can still create rules using standard modules (Inventory, Invoices, etc.), or create custom panels first.</p>
          </div>
        </div>
      )}

      {/* Rules list */}
      <div className="space-y-3" data-testid="rules-list">
        {rules.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Zap className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p className="font-medium">No automation rules yet</p>
            <p className="text-sm mt-1">Create your first rule to automate workflows</p>
          </div>
        )}

        {rules.map(r => (
          <div key={r.id} className={`p-4 rounded-lg border transition-colors ${r.is_active ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-200 opacity-70'}`} data-testid={`rule-${r.id}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Zap className={`h-4 w-4 shrink-0 ${r.is_active ? 'text-amber-500' : 'text-gray-400'}`} />
                  <span className="font-semibold text-gray-900">{r.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}`}>
                    {r.is_active ? 'Active' : 'Disabled'}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                    {TRIGGER_TYPES.find(t => t.value === r.trigger_type)?.label || r.trigger_type}
                  </span>
                </div>
                {/* Source → targets flow */}
                <div className="flex items-center gap-1.5 mt-1.5 flex-wrap text-sm">
                  <span className="text-amber-600 font-medium">{r.trigger_panel_name || 'Source'}</span>
                  <ArrowRight className="h-3 w-3 text-gray-400 shrink-0" />
                  {(r.targets || []).map((t, i) => (
                    <span key={i} className="inline-flex items-center gap-1">
                      <span className="text-green-600 font-medium">{t.target_panel_name || getTargetName(t.target_panel_id, panels)}</span>
                      <span className="text-xs text-gray-400">({ACTION_TYPES.find(a => a.value === t.action_type)?.label || t.action_type})</span>
                      {i < (r.targets || []).length - 1 && <span className="text-gray-300 mx-0.5">+</span>}
                    </span>
                  ))}
                  {r.execution_count > 0 && (
                    <span className="ml-3 text-xs text-gray-400">Executed {r.execution_count}x</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1 ml-3 shrink-0">
                <button onClick={() => toggleRule(r)} className="p-1.5 rounded-lg hover:bg-gray-100" title={r.is_active ? 'Disable' : 'Enable'} data-testid={`toggle-rule-${r.id}`}>
                  {r.is_active ? <Power className="h-4 w-4 text-green-600" /> : <PowerOff className="h-4 w-4 text-gray-400" />}
                </button>
                <button onClick={() => openEdit(r)} className="p-1.5 rounded-lg hover:bg-gray-100" data-testid={`edit-rule-${r.id}`}>
                  <Pencil className="h-4 w-4 text-gray-500" />
                </button>
                <button onClick={() => deleteRule(r.id)} className="p-1.5 rounded-lg hover:bg-red-50" data-testid={`delete-rule-${r.id}`}>
                  <Trash2 className="h-4 w-4 text-red-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════
           CREATE / EDIT MODAL
         ═══════════════════════════════════════════ */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-y-auto" data-testid="rule-modal">
          <div className="bg-white rounded-xl w-full max-w-3xl mt-6 mb-8 shadow-xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-bold">{editingRuleId ? 'Edit' : 'Create'} Automation Rule</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded" data-testid="close-modal"><X className="h-5 w-5" /></button>
            </div>

            <div className="p-4 space-y-4 max-h-[75vh] overflow-y-auto">

              {/* ── 1. Rule Name ── */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name *</label>
                <input type="text" value={rule.name} onChange={e => updateRule({ name: e.target.value })}
                  placeholder="e.g. Invoice to QC Records" className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-1 focus:ring-amber-400 focus:border-amber-400" data-testid="rule-name-input" />
              </div>

              {/* ── 2. WHEN (Source Panel + Trigger) ── */}
              <div className="p-3 bg-amber-50/70 rounded-lg border border-amber-200 space-y-3">
                <label className="block text-sm font-semibold text-amber-800">WHEN (Source Panel + Trigger)</label>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Source Panel *</label>
                    <select value={rule.trigger_panel_id}
                      onChange={e => {
                        updateRule({ trigger_panel_id: e.target.value, targets: [] });
                      }}
                      className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid="trigger-panel-select">
                      <option value="">Select panel...</option>
                      {panels.length > 0 && (
                        <optgroup label="Custom Panels">
                          {panels.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </optgroup>
                      )}
                      <optgroup label="Standard Modules">
                        {SYSTEM_MODULES.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
                      </optgroup>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Trigger Type *</label>
                    <select value={rule.trigger_type}
                      onChange={e => updateRule({ trigger_type: e.target.value })}
                      className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid="trigger-type-select">
                      {TRIGGER_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* ── 3. IF (Condition) — optional, required for condition_based ── */}
              {rule.trigger_panel_id && (
                <div className="p-3 bg-yellow-50/70 rounded-lg border border-yellow-200 space-y-3">
                  <label className="block text-sm font-semibold text-yellow-800">
                    IF (Condition) {rule.trigger_type !== 'condition_based' && <span className="text-xs font-normal text-yellow-600">-- optional</span>}
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <select value={rule.condition.field}
                      onChange={e => updateCondition({ field: e.target.value, value: '' })}
                      className="px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid="cond-field-select">
                      <option value="">Field...</option>
                      {sourceDataFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                    </select>
                    <select value={rule.condition.operator}
                      onChange={e => updateCondition({ operator: e.target.value })}
                      className="px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid="cond-op-select">
                      {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                    {!['not_empty', 'is_empty'].includes(rule.condition.operator) && (
                      condHasOptions ? (
                        <select value={rule.condition.value}
                          onChange={e => updateCondition({ value: e.target.value })}
                          className="px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid="cond-value-select">
                          <option value="">Select value...</option>
                          {condFieldInfo!.options!.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <input type="text" value={rule.condition.value}
                          onChange={e => updateCondition({ value: e.target.value })}
                          placeholder="Value" className="px-2 py-1.5 border rounded-lg text-sm" data-testid="cond-value-input" />
                      )
                    )}
                  </div>
                </div>
              )}

              {/* ── 4. TARGETS — multi-target section ── */}
              {rule.trigger_panel_id && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-green-800 flex items-center gap-1.5">
                      <Target className="h-4 w-4" /> THEN (Target Actions)
                    </label>
                    <button onClick={addTarget} type="button"
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500 text-white rounded-lg text-xs font-medium hover:bg-green-600 transition-colors"
                      data-testid="add-target-btn">
                      <Plus className="h-3.5 w-3.5" /> Add Target Panel
                    </button>
                  </div>

                  {rule.targets.length === 0 && (
                    <div className="text-center py-6 bg-green-50/50 rounded-lg border border-dashed border-green-200 text-sm text-gray-500">
                      No targets added. Click &quot;+ Add Target Panel&quot; to define what happens when this rule triggers.
                    </div>
                  )}

                  {rule.targets.map((target, tIdx) => (
                    <TargetCard
                      key={tIdx}
                      tIdx={tIdx}
                      target={target}
                      panels={panels}
                      allTargetOptions={allTargetOptions}
                      sourceDataFields={sourceDataFields}
                      sourceAllFields={sourceAllFields}
                      sourceFieldsForMapping={sourceFieldsForMapping}
                      getUpdateFields={getUpdateFields}
                      onChangePanel={handleTargetPanelChange}
                      onUpdate={updateTarget}
                      onRemove={removeTarget}
                      onAddMapping={addMappingRow}
                      onRemoveMapping={removeMappingRow}
                      onUpdateMapping={updateTargetMapping}
                      onSelectAll={selectAllMappings}
                      onToggleVis={toggleVisibility}
                      getVis={getVisibility}
                    />
                  ))}
                </div>
              )}

              {/* ── 5. PREVIEW DATA ── */}
              {previewData && previewData.length > 0 && (
                <div className="p-3 bg-indigo-50/70 rounded-lg border border-indigo-200 space-y-2" data-testid="preview-section">
                  <label className="block text-sm font-semibold text-indigo-800">Preview: Data Output</label>
                  {previewData.map((p: any, i: number) => (
                    <div key={i} className="bg-white rounded-lg border p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold text-indigo-600">{p.target_panel_name}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">{p.action_type}</span>
                        {p.data_mode && <span className="text-xs text-gray-400">{p.data_mode}</span>}
                        {p.fields_count != null && <span className="text-xs text-gray-400">{p.fields_count} fields</span>}
                      </div>
                      {/* Structured preview for update_record */}
                      {p.match && p.update ? (
                        <div className="space-y-1.5 text-xs font-mono">
                          <div className="p-2 bg-blue-50 rounded border border-blue-200">
                            <span className="font-semibold text-blue-700">MATCH: </span>
                            <span className="text-blue-600">
                              {p.match.target_field} = {String(p.match.resolved_value)}
                              {p.match.is_relation_id && <span className="text-blue-400 ml-1">(ID)</span>}
                            </span>
                          </div>
                          <div className="p-2 bg-orange-50 rounded border border-orange-200">
                            <span className="font-semibold text-orange-700">UPDATE: </span>
                            <span className="text-orange-600">
                              {p.update.target_field} = {p.update.operation}({String(p.update.resolved_value)})
                            </span>
                          </div>
                        </div>
                      ) : (
                        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto text-gray-700 font-mono" data-testid={`preview-json-${i}`}>
                          {JSON.stringify(p.preview_data, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between p-4 border-t">
              <button onClick={fetchPreview} disabled={loadingPreview || !rule.trigger_panel_id || rule.targets.length === 0}
                className="flex items-center gap-2 px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium hover:bg-indigo-200 disabled:opacity-50 transition-colors"
                data-testid="preview-btn">
                {loadingPreview ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
                Preview Data
              </button>
              <div className="flex items-center gap-3">
                <button onClick={() => setShowModal(false)} className="px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50" data-testid="cancel-btn">Cancel</button>
                <button onClick={handleSave} disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors"
                  data-testid="save-rule-btn">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {editingRuleId ? 'Update Rule' : 'Create Rule'}
                </button>
              </div>
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
              <button onClick={() => setShowLogs(false)} className="p-1 hover:bg-gray-100 rounded" data-testid="close-logs-btn"><X className="h-5 w-5" /></button>
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
                      <p className="text-gray-600 mt-1">{log.message || ''}</p>
                      <p className="text-gray-400 mt-1">{log.event} | {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}</p>
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

// ══════════════════════════════════════
// TARGET CARD COMPONENT
// ══════════════════════════════════════

interface TargetCardProps {
  tIdx: number;
  target: TargetForm;
  panels: Panel[];
  allTargetOptions: { id: string; label: string; type: 'panel' | 'system' }[];
  sourceDataFields: PanelField[];
  sourceAllFields: PanelField[];
  sourceFieldsForMapping: { key: string; label: string }[];
  getUpdateFields: (panelId: string, fields: { key: string; label: string }[]) => { key: string; label: string }[];
  onChangePanel: (tIdx: number, panelId: string) => void;
  onUpdate: (tIdx: number, patch: Partial<TargetForm>) => void;
  onRemove: (tIdx: number) => void;
  onAddMapping: (tIdx: number) => void;
  onRemoveMapping: (tIdx: number, mIdx: number) => void;
  onUpdateMapping: (tIdx: number, mIdx: number, patch: Partial<FieldMappingForm>) => void;
  onSelectAll: (tIdx: number) => void;
  onToggleVis: (tIdx: number, fieldKey: string, prop: 'visible' | 'editable', val: boolean) => void;
  getVis: (tIdx: number, fieldKey: string) => { field: string; visible: boolean; editable: boolean };
}

function TargetCard({
  tIdx, target, panels, allTargetOptions, sourceDataFields, sourceAllFields, sourceFieldsForMapping,
  getUpdateFields, onChangePanel, onUpdate, onRemove, onAddMapping, onRemoveMapping,
  onUpdateMapping, onSelectAll, onToggleVis, getVis,
}: TargetCardProps) {
  const isCreate = target.action_type === 'create_record' || target.action_type === 'create_records_per_item';
  const isUpdate = target.action_type === 'update_record';
  const updateFields = target.target_panel_id ? getUpdateFields(target.target_panel_id, target._targetFields) : [];
  const targetLabel = getTargetName(target.target_panel_id, panels);
  const isSystem = SYSTEM_MODULE_IDS.has(target.target_panel_id);

  return (
    <div className="p-3 bg-green-50/60 rounded-lg border border-green-200 space-y-3" data-testid={`target-card-${tIdx}`}>
      {/* Target header with remove button */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-green-700 flex items-center gap-1">
          <Target className="h-3.5 w-3.5" /> Target {tIdx + 1}
          {target.target_panel_id && (
            <span className="ml-1 text-green-600">
              - {targetLabel} {isSystem && <span className="text-xs text-gray-500">(System)</span>}
            </span>
          )}
        </span>
        <button onClick={() => onRemove(tIdx)} type="button"
          className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1 px-2 py-1 rounded hover:bg-red-50"
          data-testid={`remove-target-${tIdx}`}>
          <Trash2 className="h-3 w-3" /> Remove
        </button>
      </div>

      {/* Target panel + action type dropdowns */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Target Panel *</label>
          <select value={target.target_panel_id}
            onChange={e => onChangePanel(tIdx, e.target.value)}
            className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`target-panel-select-${tIdx}`}>
            <option value="">Select target...</option>
            <optgroup label="Custom Panels">
              {allTargetOptions.filter(o => o.type === 'panel').map(o => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </optgroup>
            <optgroup label="System Modules">
              {allTargetOptions.filter(o => o.type === 'system').map(o => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </optgroup>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Action Type *</label>
          <select value={target.action_type}
            onChange={e => onUpdate(tIdx, { action_type: e.target.value, field_mappings: [], field_visibility: [] })}
            className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`action-type-select-${tIdx}`}>
            {ACTION_TYPES.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>
      </div>

      {/* Data Mode toggle — only for create actions */}
      {isCreate && target.target_panel_id && (
        <div>
          <label className="block text-xs text-gray-600 mb-1.5">Data Mode</label>
          <div className="flex gap-2" data-testid={`data-mode-${tIdx}`}>
            {DATA_MODES.map(dm => (
              <button key={dm.value} type="button"
                onClick={() => onUpdate(tIdx, { data_mode: dm.value })}
                className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  target.data_mode === dm.value
                    ? 'bg-green-600 text-white border-green-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                }`}
                data-testid={`data-mode-${dm.value}-${tIdx}`}>
                {dm.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {DATA_MODES.find(dm => dm.value === target.data_mode)?.desc}
          </p>
        </div>
      )}

      {/* ── For UPDATE: MATCH CONDITION + UPDATE SECTION ── */}
      {isUpdate && target.target_panel_id && (
        <div className="space-y-3">
          {/* MATCH CONDITION */}
          <div className="p-3 bg-blue-50/70 rounded-lg border border-blue-200">
            <label className="block text-xs font-semibold text-blue-800 mb-2">
              MATCH: Find Record Where *
            </label>
            <div className="grid grid-cols-5 gap-2 items-end">
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Target Field ({targetLabel})</label>
                <select value={target.match_target_field}
                  onChange={e => onUpdate(tIdx, { match_target_field: e.target.value })}
                  className={`w-full px-2 py-1.5 border rounded-lg text-sm bg-white ${!target.match_target_field ? 'border-red-300' : ''}`}
                  data-testid={`match-target-field-${tIdx}`}>
                  <option value="">Select target field...</option>
                  {target._targetFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
              </div>
              <div className="col-span-1 text-center text-xs text-gray-400 pb-2 font-bold">=</div>
              <div className="col-span-2">
                <label className="block text-xs text-gray-500 mb-1">Source Field (from source panel)</label>
                <select value={target.match_source_field}
                  onChange={e => onUpdate(tIdx, { match_source_field: e.target.value, relation_field: e.target.value })}
                  className={`w-full px-2 py-1.5 border rounded-lg text-sm bg-white ${!target.match_source_field ? 'border-red-300' : ''}`}
                  data-testid={`match-source-field-${tIdx}`}>
                  <option value="">Select source field...</option>
                  {sourceAllFields.filter(f => f.type === 'relation').length > 0 && (
                    <optgroup label="Relation Fields (recommended)">
                      {sourceAllFields.filter(f => f.type === 'relation').map(f => (
                        <option key={f.key} value={f.key}>{f.label} (linked to {f.relatedPanel})</option>
                      ))}
                    </optgroup>
                  )}
                  <optgroup label="Data Fields">
                    {sourceDataFields.map(f => <option key={f.key} value={f.key}>{f.label} ({f.type})</option>)}
                  </optgroup>
                </select>
              </div>
            </div>
            {(!target.match_target_field || !target.match_source_field) && (
              <p className="text-xs text-red-500 mt-1.5">Both fields required: this identifies WHICH {targetLabel} record to update</p>
            )}
          </div>

          {/* UPDATE SECTION */}
          <div className="p-3 bg-orange-50/70 rounded-lg border border-orange-200">
            <label className="block text-xs font-semibold text-orange-800 mb-2">
              UPDATE: Modify Field *
            </label>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Target Field (to update)</label>
                <select value={target.update_field}
                  onChange={e => onUpdate(tIdx, { update_field: e.target.value })}
                  className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`update-field-${tIdx}`}>
                  <option value="">Select field...</option>
                  {updateFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Operation</label>
                <select value={target.update_operation}
                  onChange={e => onUpdate(tIdx, { update_operation: e.target.value })}
                  className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`update-op-${tIdx}`}>
                  {UPDATE_OPS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Value From (Source)</label>
                <select value={target.update_value_from}
                  onChange={e => onUpdate(tIdx, { update_value_from: e.target.value })}
                  className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`update-value-from-${tIdx}`}>
                  <option value="">Select field...</option>
                  <optgroup label="Data Fields (recommended)">
                    {sourceDataFields.map(f => <option key={f.key} value={f.key}>{f.label} ({f.type})</option>)}
                  </optgroup>
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── For CREATE: Relation field (optional) ── */}
      {isCreate && target.target_panel_id && (
        <div>
          <label className="block text-xs text-gray-600 mb-1">Relation Field (optional - for entity linking)</label>
          <select value={target.relation_field}
            onChange={e => onUpdate(tIdx, { relation_field: e.target.value })}
            className="w-full px-2 py-1.5 border rounded-lg text-sm bg-white" data-testid={`relation-field-select-${tIdx}`}>
            <option value="">None</option>
            {sourceAllFields.map(f => (
              <option key={f.key} value={f.key}>
                {f.label}{f.type === 'relation' ? ` (linked to ${f.relatedPanel || '?'})` : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* ── CREATE RECORD — Field Mapping ── */}
      {isCreate && target.target_panel_id && (
        <div className="space-y-2">
          {/* Full Copy mode info */}
          {target.data_mode === 'full_copy' && (
            <div className="p-2.5 bg-blue-50 rounded-lg border border-blue-200 text-xs text-blue-700" data-testid={`full-copy-info-${tIdx}`}>
              All target fields with matching source field names will be copied automatically.
              Add explicit mappings below to override or map non-matching fields.
            </div>
          )}

          {/* Smart Sync mode info */}
          {target.data_mode === 'smart_sync' && (
            <div className="p-2.5 bg-teal-50 rounded-lg border border-teal-200 text-xs text-teal-700" data-testid={`smart-sync-info-${tIdx}`}>
              Explicit mappings below take priority. Remaining target fields auto-fill from matching source fields.
            </div>
          )}

          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-gray-700">
              {target.data_mode === 'manual_only' ? 'Field Mapping (Required)' : 'Field Mapping (Overrides)'}
            </label>
            <div className="flex items-center gap-2">
              <button onClick={() => onSelectAll(tIdx)} type="button"
                className="flex items-center gap-1 text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                data-testid={`select-all-${tIdx}`}>
                <Check className="h-3 w-3" /> Select All
              </button>
              <button onClick={() => onAddMapping(tIdx)} type="button"
                className="flex items-center gap-1 text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
                data-testid={`add-mapping-${tIdx}`}>
                <Plus className="h-3 w-3" /> Add Row
              </button>
            </div>
          </div>

          {target._loadingFields ? (
            <div className="flex items-center gap-2 text-xs text-gray-500 py-2">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading target fields...
            </div>
          ) : (
            <>
              {/* Mapping header */}
              {target.field_mappings.length > 0 && (
                <div className="grid grid-cols-12 gap-2 text-xs font-semibold text-gray-500 px-1">
                  <div className="col-span-4">Target Field</div>
                  <div className="col-span-1 text-center">Type</div>
                  <div className="col-span-5">Source / Default</div>
                  <div className="col-span-2"></div>
                </div>
              )}

              {target.field_mappings.map((fm, mIdx) => (
                <div key={mIdx} className="grid grid-cols-12 gap-2 items-center" data-testid={`mapping-row-${tIdx}-${mIdx}`}>
                  <select value={fm.target_field}
                    onChange={e => onUpdateMapping(tIdx, mIdx, { target_field: e.target.value })}
                    className="col-span-4 px-2 py-1.5 border rounded text-xs bg-white" data-testid={`mapping-target-${tIdx}-${mIdx}`}>
                    <option value="">Target field...</option>
                    {target._targetFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                  </select>

                  <select value={fm.mapping_type}
                    onChange={e => onUpdateMapping(tIdx, mIdx, { mapping_type: e.target.value as any })}
                    className="col-span-1 px-1 py-1.5 border rounded text-xs bg-white" data-testid={`mapping-type-${tIdx}-${mIdx}`}>
                    <option value="field">Field</option>
                    <option value="default">Default</option>
                    <option value="reference">Ref</option>
                  </select>

                  {fm.mapping_type === 'default' ? (
                    <input type="text" value={fm.default_value}
                      onChange={e => onUpdateMapping(tIdx, mIdx, { default_value: e.target.value })}
                      placeholder="Default value" className="col-span-5 px-2 py-1.5 border rounded text-xs" data-testid={`mapping-default-${tIdx}-${mIdx}`} />
                  ) : (
                    <select value={fm.source_field}
                      onChange={e => onUpdateMapping(tIdx, mIdx, { source_field: e.target.value })}
                      className="col-span-5 px-2 py-1.5 border rounded text-xs bg-white" data-testid={`mapping-source-${tIdx}-${mIdx}`}>
                      <option value="">Source field...</option>
                      {sourceFieldsForMapping.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                    </select>
                  )}

                  <button onClick={() => onRemoveMapping(tIdx, mIdx)}
                    className="col-span-2 p-1 text-red-400 hover:text-red-600 flex justify-center"
                    data-testid={`remove-mapping-${tIdx}-${mIdx}`}>
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}

              {target.field_mappings.length === 0 && target.data_mode === 'manual_only' && (
                <p className="text-xs text-gray-400 text-center py-2">No mappings yet. Click &quot;Select All&quot; or &quot;Add Row&quot;.</p>
              )}
              {target.field_mappings.length === 0 && target.data_mode !== 'manual_only' && (
                <p className="text-xs text-gray-400 text-center py-2">
                  No explicit overrides. {target.data_mode === 'smart_sync' ? 'Matching fields auto-mapped at execution.' : 'All matching fields copied at execution.'}
                </p>
              )}
            </>
          )}

          {/* Field Visibility — show for all target fields when full_copy/smart_sync, or mapped fields for manual */}
          {(() => {
            const visFields = target.data_mode === 'manual_only'
              ? target.field_mappings.filter(fm => fm.target_field)
              : target._targetFields.map(f => ({ target_field: f.key }));
            if (visFields.length === 0) return null;
            return (
              <div className="mt-2 p-3 bg-white/80 rounded-lg border">
                <label className="text-xs font-semibold text-gray-700 mb-2 block">Field Visibility (UI display only)</label>
                <div className="space-y-1.5">
                  <div className="grid grid-cols-6 gap-2 text-xs font-semibold text-gray-500">
                    <div className="col-span-2">Field</div>
                    <div className="col-span-2 text-center">Visible</div>
                    <div className="col-span-2 text-center">Editable</div>
                  </div>
                  {visFields.map((fm, i) => {
                    const fieldKey = 'target_field' in fm ? fm.target_field : '';
                    const vis = getVis(tIdx, fieldKey);
                    const tfLabel = target._targetFields.find(f => f.key === fieldKey)?.label || fieldKey;
                    return (
                      <div key={i} className="grid grid-cols-6 gap-2 items-center text-xs">
                        <div className="col-span-2 text-gray-700">{tfLabel}</div>
                        <div className="col-span-2 text-center">
                          <input type="checkbox" checked={vis.visible}
                            onChange={e => onToggleVis(tIdx, fieldKey, 'visible', e.target.checked)}
                            className="rounded border-gray-300 text-green-600"
                            data-testid={`vis-visible-${tIdx}-${fieldKey}`} />
                        </div>
                        <div className="col-span-2 text-center">
                          <input type="checkbox" checked={vis.editable}
                            onChange={e => onToggleVis(tIdx, fieldKey, 'editable', e.target.checked)}
                            className="rounded border-gray-300 text-blue-600"
                            data-testid={`vis-editable-${tIdx}-${fieldKey}`} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
