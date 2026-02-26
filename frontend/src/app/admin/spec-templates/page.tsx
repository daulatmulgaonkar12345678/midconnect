'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAdminSpecTemplates, getAdminCategories, createAdminSpecTemplate, updateAdminSpecTemplate, deleteAdminSpecTemplate, AdminSpecTemplate, Category } from '@/lib/api';
import { Plus, Edit2, Trash2, Loader2, X, Check, AlertTriangle, Eye, EyeOff, GripVertical } from 'lucide-react';

// SSOT: camelCase for API fields (supports both camelCase and snake_case from backend)
interface SpecField {
  key: string;
  label: string;
  fieldType: string;  // SSOT: camelCase
  unit?: string;
  options?: string[];
  required?: boolean;
  displayOrder?: number;  // SSOT: camelCase
}

export default function SpecTemplatesPage() {
  const { getIdToken } = useAuth();
  const [templates, setTemplates] = useState<AdminSpecTemplate[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AdminSpecTemplate | null>(null);
  const [formData, setFormData] = useState({ name: '', categoryId: '', fields: [] as SpecField[] });  // SSOT: camelCase
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [showInactive, categoryFilter]);

  const fetchData = async () => {
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const [templatesData, categoriesData] = await Promise.all([
        getAdminSpecTemplates(token, categoryFilter || undefined, showInactive),
        getAdminCategories(token)
      ]);
      
      setTemplates(templatesData.templates);
      setCategories(categoriesData.categories);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingTemplate(null);
    setFormData({ name: '', categoryId: categories[0]?._id || '', fields: [] });  // SSOT: camelCase
    setShowModal(true);
    setError(null);
  };

  const openEditModal = (template: AdminSpecTemplate) => {
    setEditingTemplate(template);
    // Support both legacy snake_case and camelCase from backend
    const categoryId = template.categoryId || template.categoryId || '';
    
    // Transform fields to local camelCase format
    const transformedFields: SpecField[] = (template.fields || []).map((f) => ({
      key: f.key,
      label: f.label,
      fieldType: f.fieldType || f.fieldType || 'text',  // Support legacy
      unit: f.unit || '',
      options: f.options || [],
      required: f.required || false,
      displayOrder: f.displayOrder ?? f.displayOrder ?? 0  // Support legacy
    }));
    
    setFormData({
      name: template.name,
      categoryId: categoryId,  // SSOT: camelCase
      fields: transformedFields
    });
    setShowModal(true);
    setError(null);
  };

  const addField = () => {
    setFormData({
      ...formData,
      fields: [
        ...formData.fields,
        {
          key: `field_${Date.now()}`,
          label: '',
          fieldType: 'text',  // SSOT: camelCase
          unit: '',
          options: [],
          required: false,
          displayOrder: formData.fields.length  // SSOT: camelCase
        }
      ]
    });
  };

  const updateField = (index: number, updates: Partial<SpecField>) => {
    const newFields = [...formData.fields];
    newFields[index] = { ...newFields[index], ...updates };
    setFormData({ ...formData, fields: newFields });
  };

  const removeField = (index: number) => {
    setFormData({
      ...formData,
      fields: formData.fields.filter((_, i) => i !== index)
    });
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('Template name is required');
      return;
    }
    if (!formData.categoryId) {  // SSOT: camelCase
      setError('Please select a category');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      // SSOT: Transform to camelCase for backend API
      const payload = {
        name: formData.name,
        categoryId: formData.categoryId,  // SSOT: camelCase
        fields: formData.fields.map((f, i) => ({
          key: f.key || `field_${i}`,
          label: f.label,
          fieldType: f.fieldType,  // SSOT: camelCase
          unit: f.unit || '',
          options: f.options || [],
          required: f.required || false,
          displayOrder: i  // SSOT: camelCase
        }))
      };

      if (editingTemplate) {
        await updateAdminSpecTemplate(token, editingTemplate._id, payload);
      } else {
        await createAdminSpecTemplate(token, payload);
      }

      setShowModal(false);
      fetchData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (template: AdminSpecTemplate) => {
    try {
      const token = await getIdToken();
      if (!token) return;
      await updateAdminSpecTemplate(token, template._id, { isActive: !template.isActive });
      fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (template: AdminSpecTemplate) => {
    if (!confirm(`Delete spec template "${template.name}"?`)) return;

    try {
      const token = await getIdToken();
      if (!token) return;
      await deleteAdminSpecTemplate(token, template._id, true);
      fetchData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Spec Templates</h1>
          <p className="text-gray-500">Define technical specification templates for products</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          <Plus className="h-5 w-5" /> Add Template
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat._id} value={cat._id}>{cat.name}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {templates.map((template) => {
          // Support both camelCase and snake_case from backend
          const isActive = template.isActive ?? (template as { isActive?: boolean }).isActive ?? true;
          const categoryName = template.categoryName || (template as unknown as { category_name?: string }).category_name || 'Unknown';
          return (
          <div key={template._id} className={`bg-white rounded-xl shadow-sm p-6 ${!isActive ? 'opacity-60' : ''}`}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-semibold text-gray-900">{template.name}</h3>
                <p className="text-sm text-gray-500">{categoryName}</p>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                {isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
            
            <div className="mb-4">
              <p className="text-xs text-gray-500 uppercase mb-2">Fields ({template.fields?.length || 0})</p>
              <div className="space-y-1">
                {template.fields?.slice(0, 4).map((field) => {
                  // Support both camelCase and snake_case
                  const fieldType = field.fieldType || field.fieldType || 'text';
                  return (
                  <div key={field.key} className="flex items-center gap-2 text-sm">
                    <span className={`px-1.5 py-0.5 text-xs rounded ${fieldType === 'number' ? 'bg-blue-100 text-blue-700' : fieldType === 'dropdown' ? 'bg-purple-100 text-purple-700' : fieldType === 'boolean' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                      {fieldType}
                    </span>
                    <span className="text-gray-700">{field.label}</span>
                    {field.unit && <span className="text-gray-400">({field.unit})</span>}
                    {field.required && <span className="text-red-500">*</span>}
                  </div>
                  );
                })}
                {(template.fields?.length || 0) > 4 && (
                  <p className="text-xs text-gray-400">+{template.fields.length - 4} more fields</p>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2 pt-4 border-t">
              <button
                onClick={() => handleToggleActive(template)}
                className="p-2 text-gray-400 hover:text-gray-600 transition"
                title={isActive ? 'Deactivate' : 'Activate'}
              >
                {isActive ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={() => openEditModal(template)}
                className="p-2 text-gray-400 hover:text-blue-600 transition"
              >
                <Edit2 className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleDelete(template)}
                className="p-2 text-gray-400 hover:text-red-600 transition"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
          );
        })}
        {templates.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            No spec templates found. Create your first template.
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl my-8 mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{editingTemplate ? 'Edit Spec Template' : 'Create Spec Template'}</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="h-5 w-5" />
              </button>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> {error}
              </div>
            )}

            <div className="space-y-4 max-h-[60vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Template name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
                  <select
                    value={formData.categoryId}
                    onChange={(e) => setFormData({ ...formData, categoryId: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    disabled={!!editingTemplate}
                  >
                    <option value="">Select category</option>
                    {categories.map((cat) => (
                      <option key={cat._id} value={cat._id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Fields */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Specification Fields</label>
                  <button
                    type="button"
                    onClick={addField}
                    className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                  >
                    <Plus className="h-4 w-4" /> Add Field
                  </button>
                </div>
                
                <div className="space-y-3">
                  {formData.fields.map((field, index) => (
                    <div key={index} className="flex items-start gap-2 p-3 bg-gray-50 rounded-lg">
                      <GripVertical className="h-5 w-5 text-gray-400 mt-2 cursor-move" />
                      <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-2">
                        <input
                          type="text"
                          value={field.label}
                          onChange={(e) => updateField(index, { label: e.target.value, key: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                          className="px-2 py-1.5 border rounded text-sm"
                          placeholder="Label"
                        />
                        <select
                          value={field.fieldType}
                          onChange={(e) => updateField(index, { fieldType: e.target.value })}
                          className="px-2 py-1.5 border rounded text-sm"
                        >
                          <option value="text">Text</option>
                          <option value="number">Number</option>
                          <option value="dropdown">Dropdown</option>
                          <option value="boolean">Boolean</option>
                        </select>
                        {field.fieldType === 'number' && (
                          <input
                            type="text"
                            value={field.unit || ''}
                            onChange={(e) => updateField(index, { unit: e.target.value })}
                            className="px-2 py-1.5 border rounded text-sm"
                            placeholder="Unit (kg, mm)"
                          />
                        )}
                        {field.fieldType === 'dropdown' && (
                          <input
                            type="text"
                            value={field.options?.join(', ') || ''}
                            onChange={(e) => updateField(index, { options: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                            className="px-2 py-1.5 border rounded text-sm"
                            placeholder="Options (a, b, c)"
                          />
                        )}
                        <label className="flex items-center gap-1 text-sm">
                          <input
                            type="checkbox"
                            checked={field.required}
                            onChange={(e) => updateField(index, { required: e.target.checked })}
                            className="rounded"
                          />
                          Required
                        </label>
                      </div>
                      <button
                        onClick={() => removeField(index)}
                        className="p-1 text-gray-400 hover:text-red-600"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  {formData.fields.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-4">No fields added. Click "Add Field" to start.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6 pt-4 border-t">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {editingTemplate ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
