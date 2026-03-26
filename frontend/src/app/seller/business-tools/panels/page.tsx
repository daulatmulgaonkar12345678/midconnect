'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { usePermissions } from '../layout';
import { toast } from 'sonner';
import { SubscriptionBanner } from '@/components/SubscriptionGates';
import {
  LayoutGrid, Plus, Pencil, Trash2, ChevronRight, Loader2,
  Type, Hash, Calendar, ListFilter, CheckSquare, AlignLeft,
  Link2, GripVertical, X, Save, Lock, Download
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const MAX_FIELDS = 20;

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type, desc: 'Short text input' },
  { value: 'number', label: 'Number', icon: Hash, desc: 'Numeric value' },
  { value: 'date', label: 'Date', icon: Calendar, desc: 'Date picker' },
  { value: 'dropdown', label: 'Dropdown', icon: ListFilter, desc: 'Single select from options' },
  { value: 'multiselect', label: 'Multi-select', icon: ListFilter, desc: 'Multiple options' },
  { value: 'boolean', label: 'Yes / No', icon: CheckSquare, desc: 'Checkbox toggle' },
  { value: 'longtext', label: 'Long Text', icon: AlignLeft, desc: 'Multi-line text for notes' },
  { value: 'relation', label: 'Relation', icon: Link2, desc: 'Link to another module' },
];

const COLOR_OPTIONS = [
  { value: 'blue', bg: 'bg-blue-500' },
  { value: 'green', bg: 'bg-green-500' },
  { value: 'purple', bg: 'bg-purple-500' },
  { value: 'orange', bg: 'bg-orange-500' },
  { value: 'red', bg: 'bg-red-500' },
  { value: 'cyan', bg: 'bg-cyan-500' },
  { value: 'amber', bg: 'bg-amber-500' },
  { value: 'pink', bg: 'bg-pink-500' },
  { value: 'indigo', bg: 'bg-indigo-500' },
  { value: 'slate', bg: 'bg-slate-500' },
];

interface PanelField {
  key: string;
  label: string;
  type: string;
  required: boolean;
  unique?: boolean;
  options?: string[];
  relatedPanel?: string;
  relationType?: string;
  bindingField?: string;
  order: number;
  systemManaged?: boolean;
}

interface Panel {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  color: string;
  fields: PanelField[];
  allowedModules?: string[];
  allowedPanels?: string[];
  downloadEnabled?: boolean;
  createdAt: string;
  updatedAt: string;
}

interface LinkableTarget {
  id: string;
  name: string;
  type: string;
}

export default function PanelsPage() {
  const { token, isAdmin, loading: permLoading } = usePermissions();
  const router = useRouter();
  const [panels, setPanels] = useState<Panel[]>([]);
  const [loading, setLoading] = useState(true);
  const [accessLevel, setAccessLevel] = useState('standard');
  const [linkableTargets, setLinkableTargets] = useState<LinkableTarget[]>([]);
  const [maxPanels, setMaxPanels] = useState(3);

  // Create/Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingPanel, setEditingPanel] = useState<Panel | null>(null);
  const [panelName, setPanelName] = useState('');
  const [panelDesc, setPanelDesc] = useState('');
  const [panelIcon, setPanelIcon] = useState('layout-grid');
  const [panelColor, setPanelColor] = useState('blue');
  const [panelFields, setPanelFields] = useState<PanelField[]>([]);
  const [panelAllowedModules, setPanelAllowedModules] = useState<string[]>([]);
  const [panelAllowedPanels, setPanelAllowedPanels] = useState<string[]>([]);
  const [panelDownloadEnabled, setPanelDownloadEnabled] = useState(false);
  const [saving, setSaving] = useState(false);

  // Add field
  const [showFieldForm, setShowFieldForm] = useState(false);
  const [newFieldKey, setNewFieldKey] = useState('');
  const [newFieldLabel, setNewFieldLabel] = useState('');
  const [newFieldType, setNewFieldType] = useState('text');
  const [newFieldRequired, setNewFieldRequired] = useState(false);
  const [newFieldUnique, setNewFieldUnique] = useState(false);
  const [newFieldOptions, setNewFieldOptions] = useState('');
  const [newFieldRelated, setNewFieldRelated] = useState('');
  const [newFieldRelType, setNewFieldRelType] = useState('many_to_one');
  const [newFieldBindingField, setNewFieldBindingField] = useState('');
  const [targetModuleFields, setTargetModuleFields] = useState<{key: string; label: string; type: string}[]>([]);
  const [loadingModuleFields, setLoadingModuleFields] = useState(false);

  const headers = useCallback(() => ({
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json'
  }), [token]);

  const fetchPanels = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [panelsRes, accessRes, targetsRes] = await Promise.all([
        fetch(`${API_URL}/api/business-tools/panels`, { headers: headers() }),
        fetch(`${API_URL}/api/business-tools/access-level`, { headers: headers() }),
        fetch(`${API_URL}/api/business-tools/panels/linkable-targets`, { headers: headers() }),
      ]);
      if (panelsRes.ok) {
        const data = await panelsRes.json();
        setPanels(data.panels || []);
        if (data.limit !== undefined) setMaxPanels(data.limit);
      }
      if (accessRes.ok) {
        const data = await accessRes.json();
        setAccessLevel(data.level);
      }
      if (targetsRes.ok) {
        const data = await targetsRes.json();
        setLinkableTargets(data.targets || []);
      } else {
        // Fallback: at minimum show system modules
        setLinkableTargets([
          { id: 'inventory', name: 'Inventory', type: 'system' },
          { id: 'invoices', name: 'Invoices', type: 'system' },
        ]);
      }
    } catch {
      // Fallback on network error
      setLinkableTargets([
        { id: 'inventory', name: 'Inventory', type: 'system' },
        { id: 'invoices', name: 'Invoices', type: 'system' },
      ]);
    }
    setLoading(false);
  }, [token, headers]);

  useEffect(() => {
    if (!permLoading && token) fetchPanels();
  }, [permLoading, token, fetchPanels]);

  const openCreateModal = () => {
    setEditingPanel(null);
    setPanelName('');
    setPanelDesc('');
    setPanelIcon('layout-grid');
    setPanelColor('blue');
    setPanelFields([]);
    setPanelAllowedModules([]);
    setPanelAllowedPanels([]);
    setPanelDownloadEnabled(false);
    setShowFieldForm(false);
    setShowModal(true);
  };

  const openEditModal = (panel: Panel) => {
    setEditingPanel(panel);
    setPanelName(panel.name);
    setPanelDesc(panel.description);
    setPanelIcon(panel.icon);
    setPanelColor(panel.color);
    setPanelFields([...panel.fields]);
    setPanelAllowedModules(panel.allowedModules || []);
    setPanelAllowedPanels(panel.allowedPanels || []);
    setPanelDownloadEnabled(panel.downloadEnabled || false);
    setShowFieldForm(false);
    setShowModal(true);
  };

  const autoKey = (label: string) =>
    label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 50) || 'field';

  const resetFieldForm = () => {
    setNewFieldKey('');
    setNewFieldLabel('');
    setNewFieldType('text');
    setNewFieldRequired(false);
    setNewFieldUnique(false);
    setNewFieldOptions('');
    setNewFieldRelated('');
    setNewFieldRelType('many_to_one');
    setNewFieldBindingField('');
    setTargetModuleFields([]);
  };

  const fetchModuleFields = async (moduleId: string) => {
    if (!moduleId) { setTargetModuleFields([]); return; }
    setLoadingModuleFields(true);
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/module-fields/${moduleId}`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setTargetModuleFields(data.fields || []);
      }
    } catch { /* ignore */ }
    setLoadingModuleFields(false);
  };

  const addField = () => {
    if (!newFieldLabel.trim()) { toast.error('Field label is required'); return; }
    const key = newFieldKey.trim() || autoKey(newFieldLabel);
    if (panelFields.some(f => f.key === key)) { toast.error(`Duplicate field key: ${key}`); return; }
    if (panelFields.length >= MAX_FIELDS) { toast.error(`Maximum ${MAX_FIELDS} fields allowed`); return; }

    if ((newFieldType === 'dropdown' || newFieldType === 'multiselect') && !newFieldOptions.trim()) {
      toast.error('Options are required for dropdown/multi-select');
      return;
    }
    if (newFieldType === 'relation' && !newFieldRelated) {
      toast.error('Select a linked module for relation field');
      return;
    }
    if (newFieldType === 'relation' && !newFieldBindingField) {
      toast.error('Select a binding variable — the common field that links both panels');
      return;
    }

    // For relation fields, auto-set label from binding variable + target
    const targetName = linkableTargets.find(t => t.id === newFieldRelated)?.name || newFieldRelated;
    const bindingLabel = targetModuleFields.find(f => f.key === newFieldBindingField)?.label || newFieldBindingField;

    const field: PanelField = {
      key,
      label: newFieldType === 'relation' ? `${bindingLabel} (Linked to ${targetName})` : newFieldLabel.trim(),
      type: newFieldType,
      required: newFieldRequired,
      unique: newFieldUnique,
      options: ['dropdown', 'multiselect'].includes(newFieldType) ? newFieldOptions.split(',').map(o => o.trim()).filter(Boolean) : undefined,
      relatedPanel: newFieldType === 'relation' ? newFieldRelated : undefined,
      relationType: newFieldType === 'relation' ? newFieldRelType : undefined,
      bindingField: newFieldType === 'relation' ? newFieldBindingField : undefined,
      order: panelFields.length,
    };
    setPanelFields(prev => [...prev, field]);
    resetFieldForm();
    setShowFieldForm(false);
  };

  const removeField = (key: string) => {
    setPanelFields(prev => prev.filter(f => f.key !== key).map((f, i) => ({ ...f, order: i })));
  };

  const handleSave = async () => {
    if (!panelName.trim()) { toast.error('Panel name is required'); return; }
    setSaving(true);
    try {
      if (editingPanel) {
        // Update panel metadata
        const res = await fetch(`${API_URL}/api/business-tools/panels/${editingPanel.id}`, {
          method: 'PUT',
          headers: headers(),
          body: JSON.stringify({ name: panelName.trim(), description: panelDesc.trim(), icon: panelIcon, color: panelColor, allowedModules: panelAllowedModules, allowedPanels: panelAllowedPanels, downloadEnabled: panelDownloadEnabled }),
        });
        if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Update failed'); setSaving(false); return; }

        // Sync fields: delete removed, add new
        const oldKeys = new Set(editingPanel.fields.map(f => f.key));
        const newKeys = new Set(panelFields.map(f => f.key));
        const failedDeletes: string[] = [];

        for (const oldF of editingPanel.fields) {
          if (!newKeys.has(oldF.key)) {
            const delRes = await fetch(`${API_URL}/api/business-tools/panels/${editingPanel.id}/fields/${oldF.key}`, {
              method: 'DELETE', headers: headers(),
            });
            if (!delRes.ok) {
              const delData = await delRes.json().catch(() => ({ detail: 'Delete failed' }));
              failedDeletes.push(`${oldF.label}: ${delData.detail || 'Cannot delete'}`);
            }
          }
        }
        if (failedDeletes.length > 0) {
          toast.error(failedDeletes.join('\n'), { duration: 6000 });
        }
        for (const newF of panelFields) {
          if (!oldKeys.has(newF.key)) {
            await fetch(`${API_URL}/api/business-tools/panels/${editingPanel.id}/fields`, {
              method: 'POST', headers: headers(),
              body: JSON.stringify(newF),
            });
          }
        }

        // Reorder
        await fetch(`${API_URL}/api/business-tools/panels/${editingPanel.id}/fields-order`, {
          method: 'PUT', headers: headers(),
          body: JSON.stringify({ fieldKeys: panelFields.map(f => f.key) }),
        });

        toast.success('Panel updated');
      } else {
        // Create panel with fields
        const res = await fetch(`${API_URL}/api/business-tools/panels`, {
          method: 'POST',
          headers: headers(),
          body: JSON.stringify({
            name: panelName.trim(),
            description: panelDesc.trim(),
            icon: panelIcon,
            color: panelColor,
            fields: panelFields,
            allowedModules: panelAllowedModules,
            allowedPanels: panelAllowedPanels,
            downloadEnabled: panelDownloadEnabled,
          }),
        });
        if (!res.ok) { const d = await res.json(); const msg = typeof d.detail === 'object' ? d.detail.message : d.detail; toast.error(msg || 'Create failed'); setSaving(false); return; }
        toast.success('Panel created');
      }
      setShowModal(false);
      fetchPanels();
    } catch { toast.error('Operation failed'); }
    setSaving(false);
  };

  const handleDelete = async (panel: Panel) => {
    if (!confirm(`Delete panel "${panel.name}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API_URL}/api/business-tools/panels/${panel.id}`, {
        method: 'DELETE', headers: headers(),
      });
      if (!res.ok) { const d = await res.json(); const msg = typeof d.detail === 'object' ? d.detail.message : d.detail; toast.error(msg || 'Delete failed'); return; }
      toast.success('Panel deleted');
      fetchPanels();
    } catch { toast.error('Delete failed'); }
  };

  const fieldTypeIcon = (type: string) => {
    const ft = FIELD_TYPES.find(f => f.value === type);
    return ft ? ft.icon : Type;
  };

  if (permLoading || loading) {
    return <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /></div>;
  }

  if (accessLevel !== 'advanced') {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center" data-testid="panels-upgrade-required">
        <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mb-4">
          <Lock className="h-8 w-8 text-amber-500" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Advanced Access Required</h2>
        <p className="text-gray-500 mt-2 max-w-md">
          Custom Panels are available with Advanced access. Contact your platform admin to upgrade.
        </p>
        <div className="mt-4 px-4 py-2 bg-gray-100 rounded-lg text-sm text-gray-600">
          Current level: <span className="font-semibold capitalize">{accessLevel}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="panels-page">
      {/* Subscription Banner */}
      <SubscriptionBanner />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="panels-heading">Custom Panels</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Create custom data modules for your business. {panels.length}/{maxPanels === -1 ? '\u221e' : maxPanels} panels used.
          </p>
        </div>
        {isAdmin && (maxPanels === -1 || panels.length < maxPanels) && (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
            data-testid="create-panel-btn"
          >
            <Plus className="h-4 w-4" /> New Panel
          </button>
        )}
      </div>

      {/* Capacity bar */}
      <div className="bg-white rounded-lg border p-3">
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
          <span>Panel usage</span>
          <span>{panels.length} / {maxPanels === -1 ? '\u221e' : maxPanels}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${maxPanels !== -1 && panels.length >= maxPanels ? 'bg-red-500' : maxPanels !== -1 && panels.length >= maxPanels * 0.7 ? 'bg-amber-500' : 'bg-indigo-500'}`}
            style={{ width: `${maxPanels === -1 ? 10 : (panels.length / maxPanels) * 100}%` }}
          />
        </div>
      </div>

      {/* Panel Grid */}
      {panels.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border" data-testid="empty-panels">
          <LayoutGrid className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-700">No panels yet</h3>
          <p className="text-gray-400 text-sm mt-1 max-w-sm mx-auto">
            Create your first custom panel to start tracking data like QC, Dispatch, or any custom workflow.
          </p>
          {isAdmin && (
            <button onClick={openCreateModal}
              className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700"
              data-testid="create-first-panel-btn"
            >
              <Plus className="h-4 w-4 inline mr-1" /> Create First Panel
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="panel-grid">
          {panels.map(panel => (
            <div key={panel.id} className="bg-white rounded-xl border hover:shadow-md transition-shadow" data-testid={`panel-card-${panel.id}`}>
              <div className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg bg-${panel.color}-100 flex items-center justify-center`}>
                      <LayoutGrid className={`h-5 w-5 text-${panel.color}-600`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900" data-testid={`panel-name-${panel.id}`}>{panel.name}</h3>
                      {panel.description && (
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{panel.description}</p>
                      )}
                    </div>
                  </div>
                  {isAdmin && (
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEditModal(panel)}
                        className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                        data-testid={`edit-panel-${panel.id}`}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(panel)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        data-testid={`delete-panel-${panel.id}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Linked modules/panels badges */}
                {((panel.allowedModules || []).length > 0 || (panel.allowedPanels || []).length > 0) && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(panel.allowedModules || []).map(m => {
                      const moduleLabels: Record<string, string> = {
                        inventory: 'Inventory', invoices: 'Invoices', buyers: 'Buyers',
                        suppliers: 'Suppliers', purchase_orders: 'Purchase Orders',
                        quotations: 'Quotations', composite_products: 'Composite Products', employees: 'Employees',
                      };
                      return (
                        <span key={m} className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-md border border-emerald-200 font-medium">
                          <Link2 className="h-3 w-3" />
                          {moduleLabels[m] || m}
                        </span>
                      );
                    })}
                    {(panel.allowedPanels || []).map(pid => {
                      const linked = panels.find(p => p.id === pid);
                      return (
                        <span key={pid} className="inline-flex items-center gap-1 px-2 py-0.5 bg-violet-50 text-violet-700 text-xs rounded-md border border-violet-200 font-medium">
                          <Link2 className="h-3 w-3" />
                          {linked?.name || pid.slice(0, 8)}
                        </span>
                      );
                    })}
                  </div>
                )}

                <div className="mt-2 flex flex-wrap gap-1.5">
                  {panel.fields.map(f => {
                    const Icon = fieldTypeIcon(f.type);
                    return (
                      <span key={f.key} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded-md border border-gray-100">
                        <Icon className="h-3 w-3" />
                        {f.label}
                        {f.required && <span className="text-red-400">*</span>}
                      </span>
                    );
                  })}
                  {panel.fields.length === 0 && (
                    <span className="text-xs text-gray-400">No fields configured</span>
                  )}
                </div>
              </div>
              <div className="border-t px-5 py-3 flex items-center justify-between bg-gray-50/50 rounded-b-xl cursor-pointer hover:bg-gray-100/70 transition-colors"
                onClick={() => router.push(`/seller/business-tools/panels/${panel.id}`)}
                data-testid={`open-panel-${panel.id}`}
              >
                <span className="text-xs text-gray-400">{panel.fields.length} field{panel.fields.length !== 1 ? 's' : ''}</span>
                <div className="flex items-center gap-1 text-xs text-indigo-600 font-medium">
                  <span>Open Records</span>
                  <ChevronRight className="h-4 w-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()} data-testid="panel-modal">
            <div className="p-6 border-b sticky top-0 bg-white z-10 rounded-t-xl">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900">{editingPanel ? 'Edit Panel' : 'Create New Panel'}</h2>
                <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                  <X className="h-5 w-5 text-gray-500" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-5">
              {/* Panel name + description */}
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Panel Name *</label>
                  <input
                    type="text" value={panelName}
                    onChange={e => setPanelName(e.target.value)}
                    placeholder="e.g. QC Panel, Dispatch Tracking"
                    className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    data-testid="panel-name-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <input
                    type="text" value={panelDesc}
                    onChange={e => setPanelDesc(e.target.value)}
                    placeholder="Brief description of this panel"
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                    data-testid="panel-desc-input"
                  />
                </div>
              </div>

              {/* Color picker */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
                <div className="flex gap-2 flex-wrap">
                  {COLOR_OPTIONS.map(c => (
                    <button key={c.value} onClick={() => setPanelColor(c.value)}
                      className={`w-8 h-8 rounded-full ${c.bg} transition-transform ${panelColor === c.value ? 'ring-2 ring-offset-2 ring-indigo-500 scale-110' : 'hover:scale-105'}`}
                      data-testid={`color-${c.value}`}
                    />
                  ))}
                </div>
              </div>

              {/* Download toggle */}
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200" data-testid="download-toggle-section">
                <div>
                  <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
                    <Download className="h-4 w-4 text-gray-500" /> Record PDF Download
                  </label>
                  <p className="text-xs text-gray-400 mt-0.5">Allow downloading individual records as PDF</p>
                </div>
                <button
                  onClick={() => setPanelDownloadEnabled(!panelDownloadEnabled)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${panelDownloadEnabled ? 'bg-indigo-600' : 'bg-gray-300'}`}
                  data-testid="download-toggle"
                >
                  <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${panelDownloadEnabled ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              {/* Connect Panel With (Entity) */}
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-4" data-testid="panel-linking-section">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Connect Panel With (Entity)</label>
                  <p className="text-xs text-gray-400 mt-0.5">Select system modules this panel connects to. A relation field will be auto-created for each connection.</p>
                </div>

                {/* Module checkboxes */}
                <div>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Modules</span>
                  <div className="mt-2 flex flex-wrap gap-3">
                    {[
                      { key: 'inventory', label: 'Inventory' },
                      { key: 'invoices', label: 'Invoices' },
                      { key: 'buyers', label: 'Buyers' },
                      { key: 'suppliers', label: 'Suppliers' },
                      { key: 'purchase_orders', label: 'Purchase Orders' },
                      { key: 'quotations', label: 'Quotations' },
                      { key: 'composite_products', label: 'Composite Products' },
                      { key: 'employees', label: 'Employees' },
                    ].map(mod => (
                      <label key={mod.key} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={panelAllowedModules.includes(mod.key)}
                          onChange={e => {
                            if (e.target.checked) {
                              setPanelAllowedModules(prev => [...prev, mod.key]);
                            } else {
                              setPanelAllowedModules(prev => prev.filter(m => m !== mod.key));
                            }
                          }}
                          className="rounded border-gray-300 text-indigo-600 w-4 h-4"
                          data-testid={`link-module-${mod.key}`}
                        />
                        {mod.label}
                      </label>
                    ))}
                  </div>
                </div>

                {/* Panel linking dropdown */}
                <div>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Other Panels</span>
                  <p className="text-xs text-gray-400 mt-0.5 mb-2">Max 2 panels. Cannot link to itself or create circular links.</p>
                  {panelAllowedPanels.map((pid, idx) => {
                    const linked = panels.find(p => p.id === pid) || linkableTargets.find(t => t.id === pid);
                    return (
                      <div key={pid} className="flex items-center gap-2 mb-2">
                        <div className="flex-1 px-3 py-1.5 bg-white border rounded-lg text-sm text-gray-700 flex items-center gap-2">
                          <Link2 className="h-3.5 w-3.5 text-violet-500" />
                          {linked?.name || pid.slice(0, 8)}
                        </div>
                        <button onClick={() => setPanelAllowedPanels(prev => prev.filter((_, i) => i !== idx))}
                          className="p-1 text-gray-400 hover:text-red-500"
                          data-testid={`remove-linked-panel-${idx}`}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    );
                  })}
                  {panelAllowedPanels.length < 2 && (
                    <select
                      value=""
                      onChange={e => {
                        if (e.target.value && !panelAllowedPanels.includes(e.target.value)) {
                          setPanelAllowedPanels(prev => [...prev, e.target.value]);
                        }
                      }}
                      className="w-full px-3 py-2 border rounded-lg text-sm text-gray-600"
                      data-testid="add-linked-panel-select"
                    >
                      <option value="">Select a panel to link...</option>
                      {panels
                        .filter(p => p.id !== editingPanel?.id)
                        .filter(p => !panelAllowedPanels.includes(p.id))
                        .map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))
                      }
                    </select>
                  )}
                </div>
              </div>

              {/* Fields */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-gray-700">
                    Fields ({panelFields.length}/{MAX_FIELDS})
                  </label>
                  {panelFields.length < MAX_FIELDS && (
                    <button onClick={() => { resetFieldForm(); setShowFieldForm(true); }}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
                      data-testid="add-field-btn"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add Field
                    </button>
                  )}
                </div>

                {/* Existing fields */}
                <div className="space-y-2">
                  {panelFields.map((f) => {
                    const Icon = fieldTypeIcon(f.type);
                    return (
                      <div key={f.key} className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border" data-testid={`field-item-${f.key}`}>
                        <GripVertical className="h-4 w-4 text-gray-300 flex-shrink-0" />
                        <Icon className="h-4 w-4 text-gray-500 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-gray-800">{f.label}</span>
                          <span className="text-xs text-gray-400 ml-2">{f.type}{f.required ? ' (required)' : ''}{f.unique ? ' (unique)' : ''}</span>
                          {f.options && f.options.length > 0 && (
                            <span className="text-xs text-gray-400 ml-1">[ {f.options.join(', ')} ]</span>
                          )}
                          {f.relatedPanel && (
                            <span className="text-xs text-indigo-500 ml-1">
                              {(() => {
                                const moduleLabels: Record<string, string> = {
                                  inventory: 'Inventory', invoices: 'Invoices', buyers: 'Buyers',
                                  suppliers: 'Suppliers', purchase_orders: 'Purchase Orders',
                                  quotations: 'Quotations', composite_products: 'Composite Products', employees: 'Employees',
                                };
                                const name = moduleLabels[f.relatedPanel || ''] || panels.find(p => p.id === f.relatedPanel)?.name || f.relatedPanel;
                                return `Linked to ${name}`;
                              })()}
                              {f.bindingField && (
                                <span className="text-indigo-400 ml-1">via {f.bindingField}</span>
                              )}
                            </span>
                          )}
                        </div>
                        {f.systemManaged ? (
                          <span className="text-xs text-gray-400 flex items-center gap-1 flex-shrink-0 px-1.5" title="Auto-created by system">
                            <Lock className="h-3 w-3" /> Auto
                          </span>
                        ) : (
                          <button onClick={() => removeField(f.key)}
                            className="p-1 text-gray-400 hover:text-red-500 flex-shrink-0"
                            data-testid={`remove-field-${f.key}`}
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Add field form */}
                {showFieldForm && (
                  <div className="mt-3 p-4 bg-indigo-50/50 rounded-lg border border-indigo-100 space-y-3" data-testid="field-form">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Label *</label>
                        <input type="text" value={newFieldLabel}
                          onChange={e => {
                            setNewFieldLabel(e.target.value);
                            if (!newFieldKey || newFieldKey === autoKey(newFieldLabel)) setNewFieldKey(autoKey(e.target.value));
                          }}
                          placeholder="e.g. QC Status"
                          className="w-full px-2.5 py-1.5 border rounded-lg text-sm"
                          data-testid="field-label-input"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Key</label>
                        <input type="text" value={newFieldKey}
                          onChange={e => setNewFieldKey(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                          placeholder="auto-generated"
                          className="w-full px-2.5 py-1.5 border rounded-lg text-sm font-mono text-gray-500"
                          data-testid="field-key-input"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1.5">Type</label>
                      <div className="grid grid-cols-4 gap-1.5">
                        {FIELD_TYPES.map(ft => {
                          const Icon = ft.icon;
                          return (
                            <button key={ft.value} onClick={() => setNewFieldType(ft.value)}
                              className={`flex flex-col items-center gap-1 px-2 py-2 rounded-lg text-xs border transition-colors ${
                                newFieldType === ft.value
                                  ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                              }`}
                              data-testid={`field-type-${ft.value}`}
                            >
                              <Icon className="h-4 w-4" />
                              {ft.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Options for dropdown/multiselect */}
                    {(newFieldType === 'dropdown' || newFieldType === 'multiselect') && (
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Options (comma-separated)
                        </label>
                        <input type="text" value={newFieldOptions}
                          onChange={e => setNewFieldOptions(e.target.value)}
                          placeholder="Pass, Fail, Pending"
                          className="w-full px-2.5 py-1.5 border rounded-lg text-sm"
                          data-testid="field-options-input"
                        />
                      </div>
                    )}

                    {/* Relation config */}
                    {newFieldType === 'relation' && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Link To</label>
                            <select value={newFieldRelated} onChange={e => {
                              setNewFieldRelated(e.target.value);
                              setNewFieldBindingField('');
                              setTargetModuleFields([]);
                              if (e.target.value) fetchModuleFields(e.target.value);
                            }}
                              className="w-full px-2.5 py-1.5 border rounded-lg text-sm"
                              data-testid="field-related-select"
                            >
                              <option value="">Select module...</option>
                              <optgroup label="System Modules">
                                <option value="inventory">Inventory</option>
                                <option value="invoices">Invoices</option>
                                <option value="buyers">Buyers</option>
                                <option value="suppliers">Suppliers</option>
                                <option value="purchase_orders">Purchase Orders</option>
                                <option value="quotations">Quotations</option>
                                <option value="composite_products">Composite Products</option>
                                <option value="employees">Employees</option>
                              </optgroup>
                              {panels.length > 0 && (
                                <optgroup label="Custom Panels">
                                  {panels.map(p => (
                                    <option key={p.id} value={p.id}>{p.name}</option>
                                  ))}
                                </optgroup>
                              )}
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Relation Type</label>
                            <select value={newFieldRelType} onChange={e => setNewFieldRelType(e.target.value)}
                              className="w-full px-2.5 py-1.5 border rounded-lg text-sm"
                              data-testid="field-reltype-select"
                            >
                              <option value="many_to_one">Many to One (default)</option>
                              <option value="one_to_one">One to One</option>
                            </select>
                          </div>
                        </div>

                        {/* Binding Variable — appears after selecting a target */}
                        {newFieldRelated && (
                          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <label className="block text-xs font-semibold text-blue-800 mb-1">
                              Binding Variable (Common Field)
                            </label>
                            <p className="text-xs text-blue-600 mb-2">
                              Select which field from the target is the common reference. This is how the system identifies and links records.
                            </p>
                            {loadingModuleFields ? (
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <Loader2 className="h-3 w-3 animate-spin" /> Loading fields...
                              </div>
                            ) : (
                              <select value={newFieldBindingField} onChange={e => {
                                setNewFieldBindingField(e.target.value);
                                // Auto-set label from binding field + target name
                                if (e.target.value) {
                                  const bf = targetModuleFields.find(f => f.key === e.target.value);
                                  const tn = linkableTargets.find(t => t.id === newFieldRelated)?.name || newFieldRelated;
                                  if (bf) {
                                    setNewFieldLabel(`${bf.label} (Linked to ${tn})`);
                                    setNewFieldKey(autoKey(bf.label));
                                  }
                                }
                              }}
                                className="w-full px-2.5 py-1.5 border rounded-lg text-sm bg-white"
                                data-testid="field-binding-select"
                              >
                                <option value="">Select binding variable...</option>
                                {targetModuleFields.map(f => (
                                  <option key={f.key} value={f.key}>
                                    {f.label} ({f.type})
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex items-center gap-4">
                      <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                        <input type="checkbox" checked={newFieldRequired}
                          onChange={e => setNewFieldRequired(e.target.checked)}
                          className="rounded border-gray-300 text-indigo-600"
                          data-testid="field-required-checkbox"
                        />
                        Required
                      </label>
                      <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                        <input type="checkbox" checked={newFieldUnique}
                          onChange={e => setNewFieldUnique(e.target.checked)}
                          className="rounded border-gray-300 text-amber-600"
                          data-testid="field-unique-checkbox"
                        />
                        Unique
                      </label>
                    </div>

                    <div className="flex gap-2 pt-1">
                      <button onClick={addField}
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700"
                        data-testid="confirm-add-field-btn"
                      >
                        Add Field
                      </button>
                      <button onClick={() => setShowFieldForm(false)}
                        className="px-3 py-1.5 text-gray-500 hover:text-gray-700 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t bg-gray-50/50 rounded-b-xl flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
                Cancel
              </button>
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                data-testid="save-panel-btn"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Saving...' : editingPanel ? 'Update Panel' : 'Create Panel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
