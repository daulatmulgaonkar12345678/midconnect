'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import type { GlobalDropdown, DropdownValue } from '@/types';
import { 
  getGlobalDropdowns, 
  createGlobalDropdown, 
  updateGlobalDropdown, 
  deleteGlobalDropdown,
  seedSystemDropdowns
} from '@/lib/api';
import { 
  Plus, 
  Edit2, 
  Trash2, 
  Loader2, 
  AlertCircle, 
  Check, 
  X, 
  Lock,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Database
} from 'lucide-react';

export default function GlobalDropdownsPage() {
  const { getIdToken } = useAuth();
  const [dropdowns, setDropdowns] = useState<GlobalDropdown[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  
  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editingDropdown, setEditingDropdown] = useState<GlobalDropdown | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Expanded dropdowns
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  
  // Form state
  const [formData, setFormData] = useState({
    key: '',
    name: '',
    description: '',
    values: [{ value: '', label: '', displayOrder: 0 }] as DropdownValue[]
  });

  const loadDropdowns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      const result = await getGlobalDropdowns(token, { 
        includeInactive: showInactive,
        includeSystem: true 
      });
      setDropdowns(result.dropdowns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dropdowns');
    } finally {
      setLoading(false);
    }
  }, [getIdToken, showInactive]);

  useEffect(() => {
    loadDropdowns();
  }, [loadDropdowns]);

  const handleSeedDefaults = async () => {
    if (!confirm('This will create default system dropdowns (Unit System, Seller Types, etc.). Continue?')) {
      return;
    }
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      await seedSystemDropdowns(token);
      await loadDropdowns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to seed dropdowns');
    }
  };

  const openCreateModal = () => {
    setEditingDropdown(null);
    setFormData({
      key: '',
      name: '',
      description: '',
      values: [{ value: '', label: '', displayOrder: 0, isActive: true }]
    });
    setModalOpen(true);
  };

  const openEditModal = (dropdown: GlobalDropdown) => {
    setEditingDropdown(dropdown);
    setFormData({
      key: dropdown.key,
      name: dropdown.name,
      description: dropdown.description || '',
      values: dropdown.values.length > 0 
        ? dropdown.values 
        : [{ value: '', label: '', displayOrder: 0, isActive: true }]
    });
    setModalOpen(true);
  };

  const addValue = () => {
    setFormData(prev => ({
      ...prev,
      values: [...prev.values, { 
        value: '', 
        label: '', 
        displayOrder: prev.values.length,
        isActive: true 
      }]
    }));
  };

  const removeValue = (index: number) => {
    if (formData.values.length <= 1) return;
    setFormData(prev => ({
      ...prev,
      values: prev.values.filter((_, i) => i !== index)
    }));
  };

  const updateValue = (index: number, field: keyof DropdownValue, value: string | number | boolean) => {
    setFormData(prev => ({
      ...prev,
      values: prev.values.map((v, i) => i === index ? { ...v, [field]: value } : v)
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      // Validate
      if (!formData.key || !formData.name) {
        throw new Error('Key and Name are required');
      }
      
      const validValues = formData.values.filter(v => v.value && v.label);
      if (validValues.length === 0) {
        throw new Error('At least one value is required');
      }
      
      if (editingDropdown) {
        // Update existing
        await updateGlobalDropdown(token, editingDropdown.key, {
          name: formData.name,
          description: formData.description || undefined,
          values: validValues.map((v, i) => ({
            value: v.value,
            label: v.label,
            displayOrder: v.displayOrder ?? i,
            isActive: v.isActive ?? true
          }))
        });
      } else {
        // Create new
        await createGlobalDropdown(token, {
          key: formData.key.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
          name: formData.name,
          description: formData.description || undefined,
          values: validValues.map((v, i) => ({
            value: v.value.toLowerCase().replace(/[^a-z0-9_-]/g, '_'),
            label: v.label,
            displayOrder: v.displayOrder ?? i
          }))
        });
      }
      
      setModalOpen(false);
      await loadDropdowns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save dropdown');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (dropdown: GlobalDropdown) => {
    if (dropdown.isSystem) {
      alert('Cannot delete system dropdowns');
      return;
    }
    
    if (!confirm(`Delete dropdown "${dropdown.name}"? This may affect spec templates using it.`)) {
      return;
    }
    
    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');
      
      await deleteGlobalDropdown(token, dropdown.key, true);
      await loadDropdowns();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete dropdown');
    }
  };

  const toggleExpanded = (key: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Global Dropdowns</h1>
          <p className="text-gray-600 mt-1">
            Define reusable dropdown options (units, seller types, materials, etc.)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSeedDefaults}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Database className="h-4 w-4" />
            Seed Defaults
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Add Dropdown
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-red-700">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="h-4 w-4 text-red-600" />
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => setShowInactive(e.target.checked)}
            className="rounded border-gray-300"
          />
          Show inactive
        </label>
        <button
          onClick={loadDropdowns}
          className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Dropdowns List */}
      {dropdowns.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Dropdowns Yet</h3>
          <p className="text-gray-600 mb-4">
            Create global dropdowns to define reusable options for categories and products.
          </p>
          <button
            onClick={handleSeedDefaults}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Database className="h-4 w-4" />
            Seed Default Dropdowns
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm divide-y">
          {dropdowns.map((dropdown) => (
            <div key={dropdown.key} className="p-4">
              <div 
                className="flex items-center justify-between cursor-pointer"
                onClick={() => toggleExpanded(dropdown.key)}
              >
                <div className="flex items-center gap-3">
                  {expandedKeys.has(dropdown.key) ? (
                    <ChevronUp className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900">{dropdown.name}</h3>
                      {dropdown.isSystem && (
                        <span className="flex items-center gap-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                          <Lock className="h-3 w-3" /> System
                        </span>
                      )}
                      {!dropdown.isActive && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500">
                      Key: <code className="bg-gray-100 px-1 rounded">{dropdown.key}</code>
                      {' • '}
                      {dropdown.values.length} values
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => openEditModal(dropdown)}
                    className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                    title="Edit"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  {!dropdown.isSystem && (
                    <button
                      onClick={() => handleDelete(dropdown)}
                      className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
              
              {/* Expanded values */}
              {expandedKeys.has(dropdown.key) && (
                <div className="mt-4 ml-8 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {dropdown.values.map((v) => (
                    <div 
                      key={v.value}
                      className={`px-3 py-2 rounded-lg border ${
                        v.isActive 
                          ? 'bg-gray-50 border-gray-200' 
                          : 'bg-gray-100 border-gray-300 opacity-50'
                      }`}
                    >
                      <p className="font-medium text-sm text-gray-900">{v.label}</p>
                      <p className="text-xs text-gray-500">{v.value}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <form onSubmit={handleSubmit}>
              <div className="p-6 border-b">
                <h2 className="text-xl font-semibold">
                  {editingDropdown ? 'Edit Dropdown' : 'Create Dropdown'}
                </h2>
              </div>
              
              <div className="p-6 space-y-4">
                {/* Key */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Key <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.key}
                    onChange={(e) => setFormData(prev => ({ ...prev, key: e.target.value }))}
                    disabled={!!editingDropdown}
                    placeholder="e.g., material_type"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Lowercase letters, numbers, underscores only. Cannot be changed after creation.
                  </p>
                </div>
                
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Display Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Material Type"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                
                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Optional description..."
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                
                {/* Values */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Values <span className="text-red-500">*</span>
                    </label>
                    <button
                      type="button"
                      onClick={addValue}
                      className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                    >
                      <Plus className="h-4 w-4" /> Add Value
                    </button>
                  </div>
                  
                  <div className="space-y-2">
                    {formData.values.map((v, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={v.value}
                          onChange={(e) => updateValue(index, 'value', e.target.value)}
                          placeholder="value_key"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        />
                        <input
                          type="text"
                          value={v.label}
                          onChange={(e) => updateValue(index, 'label', e.target.value)}
                          placeholder="Display Label"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        />
                        <input
                          type="number"
                          value={v.displayOrder}
                          onChange={(e) => updateValue(index, 'displayOrder', parseInt(e.target.value) || 0)}
                          placeholder="Order"
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => removeValue(index)}
                          disabled={formData.values.length <= 1}
                          className="p-2 text-gray-400 hover:text-red-600 disabled:opacity-50"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="p-6 border-t bg-gray-50 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Check className="h-4 w-4" />
                      {editingDropdown ? 'Update' : 'Create'}
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
