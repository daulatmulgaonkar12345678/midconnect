'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { usePermissions } from '../layout';
import { toast } from 'sonner';
import {
  LayoutGrid, Plus, Pencil, Trash2, ChevronRight, Loader2,
  Type, Hash, Calendar, ListFilter, CheckSquare, AlignLeft,
  Link2, GripVertical, X, Save, AlertTriangle, Lock
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

const MAX_PANELS = 10;
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

const ICON_OPTIONS = [
  'layout-grid', 'clipboard-check', 'truck', 'package', 'shield-check',
  'file-text', 'bar-chart', 'users', 'settings', 'zap',
  'target', 'star', 'flag', 'tag', 'layers',
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
  order: number;
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

  // Create/Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingPanel, setEditingPanel] = useState<Panel | null>(null);
  const [panelName, setPanelName] = useState('');
  const [panelDesc, setPanelDesc] = useState('');
  const [panelIcon, setPanelIcon] = useState('layout-grid');
  const [panelColor, setPanelColor] = useState('blue');
  const [panelFields, setPanelFields] = useState<PanelField[]>([]);
  const [panelAllowedModules, setPanelAllowedModules] = useState<string[]>([]);
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
      }
      if (accessRes.ok) {
        const data = await accessRes.json();
        setAccessLevel(data.level);
      }
      if (targetsRes.ok) {
        const data = await targetsRes.json();
        setLinkableTargets(data.targets || []);
      }
    } catch { /* empty */ }
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
    setShowFieldForm(false);
  };

  const openEditModal = (panel: Panel) => {
    setEditingPanel(panel);
    setPanelName(panel.name);
    setPanelDesc(panel.description);
    setPanelIcon(panel.icon);
    setPanelColor(panel.color);
    setPanelFields([...panel.fields]);
    setPanelAllowedModules(panel.allowedModules || []);
    setShowFieldForm(false);
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

    const field: PanelField = {
      key,
      label: newFieldLabel.trim(),
      type: newFieldType,
      required: newFieldRequired,
      unique: newFieldUnique,
      options: ['dropdown', 'multiselect'].includes(newFieldType) ? newFieldOptions.split(',').map(o => o.trim()).filter(Boolean) : undefined,
      relatedPanel: newFieldType === 'relation' ? newFieldRelated : undefined,
      relationType: newFieldType === 'relation' ? newFieldRelType : undefined,
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
          body: JSON.stringify({ name: panelName.trim(), description: panelDesc.trim(), icon: panelIcon, color: panelColor, allowedModules: panelAllowedModules }),
        });
        if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Update failed'); setSaving(false); return; }

        // Sync fields: delete removed, add new
        const oldKeys = new Set(editingPanel.fields.map(f => f.key));
        const newKeys = new Set(panelFields.map(f => f.key));

        for (const oldF of editingPanel.fields) {
          if (!newKeys.has(oldF.key)) {
            await fetch(`${API_URL}/api/business-tools/panels/${editingPanel.id}/fields/${oldF.key}`, {
              method: 'DELETE', headers: headers(),
            });
          }
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
          }),
        });
        if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Create failed'); setSaving(false); return; }
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
      if (!res.ok) { const d = await res.json(); toast.error(d.detail || 'Delete failed'); return; }
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" data-testid="panels-heading">Custom Panels</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Create custom data modules for your business. {panels.length}/{MAX_PANELS} panels used.
          </p>
        </div>
        {isAdmin && panels.length < MAX_PANELS && (
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
          <span>{panels.length} / {MAX_PANELS}</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${panels.length >= MAX_PANELS ? 'bg-red-500' : panels.length >= MAX_PANELS * 0.7 ? 'bg-amber-500' : 'bg-indigo-500'}`}
            style={{ width: `${(panels.length / MAX_PANELS) * 100}%` }}
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

                <div className="mt-4 flex flex-wrap gap-1.5">
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
                  {panelFields.map((f, idx) => {
                    const Icon = fieldTypeIcon(f.type);
                    return (
                      <div key={f.key} className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border" data-testid={`field-item-${f.key}`}>
                        <GripVertical className="h-4 w-4 text-gray-300 flex-shrink-0" />
                        <Icon className="h-4 w-4 text-gray-500 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-gray-800">{f.label}</span>
                          <span className="text-xs text-gray-400 ml-2">{f.type}{f.required ? ' (required)' : ''}</span>
                          {f.options && f.options.length > 0 && (
                            <span className="text-xs text-gray-400 ml-1">[ {f.options.join(', ')} ]</span>
                          )}
                          {f.relatedPanel && (
                            <span className="text-xs text-indigo-500 ml-1">
                              linked to: {linkableTargets.find(t => t.id === f.relatedPanel)?.name || f.relatedPanel}
                            </span>
                          )}
                        </div>
                        <button onClick={() => removeField(f.key)}
                          className="p-1 text-gray-400 hover:text-red-500 flex-shrink-0"
                          data-testid={`remove-field-${f.key}`}
                        >
                          <X className="h-4 w-4" />
                        </button>
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
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">Link To</label>
                          <select value={newFieldRelated} onChange={e => setNewFieldRelated(e.target.value)}
                            className="w-full px-2.5 py-1.5 border rounded-lg text-sm"
                            data-testid="field-related-select"
                          >
                            <option value="">Select module...</option>
                            {linkableTargets.map(t => (
                              <option key={t.id} value={t.id}>{t.name} ({t.type})</option>
                            ))}
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
                    )}

                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                        <input type="checkbox" checked={newFieldRequired}
                          onChange={e => setNewFieldRequired(e.target.checked)}
                          className="rounded border-gray-300 text-indigo-600"
                          data-testid="field-required-checkbox"
                        />
                        Required
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
