'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { getAdminSpecTemplates, getAdminCategories, createAdminSpecTemplate, updateAdminSpecTemplate, deleteAdminSpecTemplate, AdminSpecTemplate, Category } from '@/lib/api';
import { Plus, Edit2, Trash2, Loader2, X, Check, AlertTriangle, Eye, EyeOff, GripVertical, Calculator, Layers } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

// SSOT: camelCase for API fields
interface SpecField {
  key: string;
  label: string;
  fieldType: string;
  unit?: string;
  options?: string[];
  required?: boolean;
  displayOrder?: number;
}

// Supported shapes for raw material calculations
const FORMULA_TYPES = [
  { key: 'round_bar', label: 'Round Bar', description: 'V = π × (d/2)² × L' },
  { key: 'square_bar', label: 'Square Bar', description: 'V = side² × L' },
  { key: 'pipe', label: 'Pipe / Tube', description: 'V = π × ((OD/2)² - ((OD-2t)/2)²) × L' },
  { key: 'plate', label: 'Plate', description: 'V = thickness × width × length' },
  { key: 'sheet', label: 'Sheet', description: 'V = thickness × width × length' },
];

// Extended template type with raw material fields
interface ExtendedTemplate extends Omit<AdminSpecTemplate, 'templateType' | 'formulaType'> {
  templateType?: string;
  formulaType?: string;
  supportedShapes?: string[];
}

interface FormData {
  name: string;
  categoryId: string;
  fields: SpecField[];
  templateType: 'standard' | 'raw_material';
  formulaType: string;
  supportedShapes: string[];
}

export default function SpecTemplatesPage() {
  const { getIdToken } = useAuth();
  const [templates, setTemplates] = useState<ExtendedTemplate[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [templateTypeFilter, setTemplateTypeFilter] = useState<string>('');
  const [showModal, setShowModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ExtendedTemplate | null>(null);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    categoryId: '',
    fields: [],
    templateType: 'standard',
    formulaType: '',
    supportedShapes: []
  });
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
      
      setTemplates(templatesData.templates as ExtendedTemplate[]);
      setCategories(categoriesData.categories);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingTemplate(null);
    setFormData({
      name: '',
      categoryId: categories[0]?._id || '',
      fields: [],
      templateType: 'standard',
      formulaType: '',
      supportedShapes: []
    });
    setShowModal(true);
    setError(null);
  };

  const openEditModal = (template: ExtendedTemplate) => {
    setEditingTemplate(template);
    const categoryId = template.categoryId || '';
    
    // Transform fields to local format
    const transformedFields: SpecField[] = (template.fields || []).map((f) => ({
      key: f.key,
      label: f.label,
      fieldType: f.fieldType || 'text',
      unit: f.unit || '',
      options: f.options || [],
      required: f.required || false,
      displayOrder: f.displayOrder ?? 0
    }));
    
    setFormData({
      name: template.name,
      categoryId: categoryId,
      fields: transformedFields,
      templateType: (template.templateType as 'standard' | 'raw_material') || 'standard',
      formulaType: template.formulaType || '',
      supportedShapes: template.supportedShapes || []
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
          fieldType: 'text',
          unit: '',
          options: [],
          required: false,
          displayOrder: formData.fields.length
        }
      ]
    });
  };

  // Auto-populate fields based on formula type for raw materials
  const autoPopulateRawMaterialFields = (formulaType: string) => {
    const fieldTemplates: Record<string, SpecField[]> = {
      round_bar: [
        { key: 'diameter', label: 'Diameter', fieldType: 'number', unit: 'mm', required: true, displayOrder: 0 },
        { key: 'length', label: 'Length', fieldType: 'number', unit: 'meter', required: true, displayOrder: 1 },
        { key: 'quantity', label: 'Quantity', fieldType: 'number', unit: 'pieces', required: true, displayOrder: 2 },
      ],
      square_bar: [
        { key: 'side', label: 'Side', fieldType: 'number', unit: 'mm', required: true, displayOrder: 0 },
        { key: 'length', label: 'Length', fieldType: 'number', unit: 'meter', required: true, displayOrder: 1 },
        { key: 'quantity', label: 'Quantity', fieldType: 'number', unit: 'pieces', required: true, displayOrder: 2 },
      ],
      pipe: [
        { key: 'outer_diameter', label: 'Outer Diameter (OD)', fieldType: 'number', unit: 'mm', required: true, displayOrder: 0 },
        { key: 'thickness', label: 'Wall Thickness', fieldType: 'number', unit: 'mm', required: true, displayOrder: 1 },
        { key: 'length', label: 'Length', fieldType: 'number', unit: 'meter', required: true, displayOrder: 2 },
        { key: 'quantity', label: 'Quantity', fieldType: 'number', unit: 'pieces', required: true, displayOrder: 3 },
      ],
      plate: [
        { key: 'thickness', label: 'Thickness', fieldType: 'number', unit: 'mm', required: true, displayOrder: 0 },
        { key: 'width', label: 'Width', fieldType: 'number', unit: 'mm', required: true, displayOrder: 1 },
        { key: 'length', label: 'Length', fieldType: 'number', unit: 'meter', required: true, displayOrder: 2 },
        { key: 'quantity', label: 'Quantity', fieldType: 'number', unit: 'pieces', required: true, displayOrder: 3 },
      ],
      sheet: [
        { key: 'thickness', label: 'Thickness', fieldType: 'number', unit: 'mm', required: true, displayOrder: 0 },
        { key: 'width', label: 'Width', fieldType: 'number', unit: 'mm', required: true, displayOrder: 1 },
        { key: 'length', label: 'Length', fieldType: 'number', unit: 'meter', required: true, displayOrder: 2 },
        { key: 'quantity', label: 'Quantity', fieldType: 'number', unit: 'pieces', required: true, displayOrder: 3 },
      ],
    };

    if (fieldTemplates[formulaType]) {
      setFormData(prev => ({
        ...prev,
        fields: fieldTemplates[formulaType]
      }));
    }
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

  const toggleSupportedShape = (shape: string) => {
    const shapes = formData.supportedShapes.includes(shape)
      ? formData.supportedShapes.filter(s => s !== shape)
      : [...formData.supportedShapes, shape];
    setFormData({ ...formData, supportedShapes: shapes });
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      setError('Template name is required');
      return;
    }
    if (!formData.categoryId) {
      setError('Please select a category');
      return;
    }
    if (formData.templateType === 'raw_material' && !formData.formulaType) {
      setError('Please select a formula type for raw material templates');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const payload = {
        name: formData.name,
        categoryId: formData.categoryId,
        fields: formData.fields.map((f, i) => ({
          key: f.key || `field_${i}`,
          label: f.label,
          fieldType: f.fieldType,
          unit: f.unit || '',
          options: f.options || [],
          required: f.required || false,
          displayOrder: i
        })),
        templateType: formData.templateType,
        formulaType: formData.templateType === 'raw_material' ? formData.formulaType : null,
        supportedShapes: formData.templateType === 'raw_material' ? formData.supportedShapes : []
      };

      if (editingTemplate) {
        await updateAdminSpecTemplate(token, editingTemplate._id, payload);
      } else {
        await createAdminSpecTemplate(token, payload);
      }

      setShowModal(false);
      fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save template');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (template: ExtendedTemplate) => {
    try {
      const token = await getIdToken();
      if (!token) return;
      await updateAdminSpecTemplate(token, template._id, { isActive: !template.isActive });
      fetchData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update');
    }
  };

  const handleDelete = async (template: ExtendedTemplate) => {
    if (!confirm(`Delete spec template "${template.name}"?`)) return;

    try {
      const token = await getIdToken();
      if (!token) return;
      await deleteAdminSpecTemplate(token, template._id, true);
      fetchData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    }
  };

  // Filter templates
  const filteredTemplates = templates.filter(t => {
    if (templateTypeFilter && t.templateType !== templateTypeFilter) return false;
    return true;
  });

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
          data-testid="add-template-btn"
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
            data-testid="category-filter"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat._id} value={cat._id}>{cat.name}</option>
            ))}
          </select>
          <select
            value={templateTypeFilter}
            onChange={(e) => setTemplateTypeFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            data-testid="type-filter"
          >
            <option value="">All Types</option>
            <option value="standard">Standard</option>
            <option value="raw_material">Raw Material</option>
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
        {filteredTemplates.map((template) => {
          const isActive = template.isActive ?? true;
          const categoryName = template.categoryName || 'Unknown';
          const isRawMaterial = template.templateType === 'raw_material';
          
          return (
            <div 
              key={template._id} 
              className={`bg-white rounded-xl shadow-sm p-6 border-2 ${
                isRawMaterial ? 'border-orange-200' : 'border-transparent'
              } ${!isActive ? 'opacity-60' : ''}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    {isRawMaterial && <Calculator className="h-4 w-4 text-orange-500" />}
                    <h3 className="font-semibold text-gray-900">{template.name}</h3>
                  </div>
                  <p className="text-sm text-gray-500">{categoryName}</p>
                </div>
                <div className="flex flex-col gap-1 items-end">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {isActive ? 'Active' : 'Inactive'}
                  </span>
                  {isRawMaterial && (
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-700">
                      Raw Material
                    </span>
                  )}
                </div>
              </div>
              
              {/* Formula info for raw materials */}
              {isRawMaterial && template.formulaType && (
                <div className="mb-3 p-2 bg-orange-50 rounded-lg">
                  <p className="text-xs text-orange-600 font-medium">
                    Formula: {FORMULA_TYPES.find(f => f.key === template.formulaType)?.label || template.formulaType}
                  </p>
                  {template.supportedShapes && template.supportedShapes.length > 0 && (
                    <p className="text-xs text-orange-500 mt-1">
                      Shapes: {template.supportedShapes.join(', ')}
                    </p>
                  )}
                </div>
              )}
              
              <div className="mb-4">
                <p className="text-xs text-gray-500 uppercase mb-2">Fields ({template.fields?.length || 0})</p>
                <div className="space-y-1">
                  {template.fields?.slice(0, 4).map((field) => {
                    const fieldType = field.fieldType || 'text';
                    return (
                      <div key={field.key} className="flex items-center gap-2 text-sm">
                        <span className={`px-1.5 py-0.5 text-xs rounded ${
                          fieldType === 'number' ? 'bg-blue-100 text-blue-700' : 
                          fieldType === 'dropdown' ? 'bg-purple-100 text-purple-700' : 
                          fieldType === 'boolean' ? 'bg-green-100 text-green-700' : 
                          'bg-gray-100 text-gray-700'
                        }`}>
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
                  data-testid={`edit-template-${template._id}`}
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
        {filteredTemplates.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            No spec templates found. Create your first template.
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl my-8 mx-4">
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

            <div className="space-y-4 max-h-[65vh] overflow-y-auto pr-2">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="Template name"
                    data-testid="template-name-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category *</label>
                  <select
                    value={formData.categoryId}
                    onChange={(e) => setFormData({ ...formData, categoryId: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    disabled={!!editingTemplate}
                    data-testid="template-category-select"
                  >
                    <option value="">Select category</option>
                    {categories.map((cat) => (
                      <option key={cat._id} value={cat._id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Template Type */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-3">Template Type</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="templateType"
                      value="standard"
                      checked={formData.templateType === 'standard'}
                      onChange={() => setFormData({ ...formData, templateType: 'standard', formulaType: '', supportedShapes: [] })}
                      className="text-blue-600"
                    />
                    <Layers className="h-4 w-4 text-gray-500" />
                    <span className="text-sm">Standard Template</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="templateType"
                      value="raw_material"
                      checked={formData.templateType === 'raw_material'}
                      onChange={() => setFormData({ ...formData, templateType: 'raw_material' })}
                      className="text-orange-600"
                      data-testid="raw-material-radio"
                    />
                    <Calculator className="h-4 w-4 text-orange-500" />
                    <span className="text-sm">Raw Material (Calculator)</span>
                  </label>
                </div>
              </div>

              {/* Raw Material Configuration */}
              {formData.templateType === 'raw_material' && (
                <div className="p-4 bg-orange-50 rounded-lg space-y-4">
                  <h4 className="font-medium text-orange-800 flex items-center gap-2">
                    <Calculator className="h-4 w-4" /> Raw Material Configuration
                  </h4>
                  
                  {/* Formula Type */}
                  <div>
                    <label className="block text-sm font-medium text-orange-700 mb-2">Primary Formula Type *</label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {FORMULA_TYPES.map((formula) => (
                        <label
                          key={formula.key}
                          className={`flex flex-col p-3 border-2 rounded-lg cursor-pointer transition ${
                            formData.formulaType === formula.key 
                              ? 'border-orange-500 bg-orange-100' 
                              : 'border-gray-200 hover:border-orange-300'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="radio"
                              name="formulaType"
                              value={formula.key}
                              checked={formData.formulaType === formula.key}
                              onChange={() => {
                                setFormData({ ...formData, formulaType: formula.key });
                                autoPopulateRawMaterialFields(formula.key);
                              }}
                              className="text-orange-600"
                              data-testid={`formula-${formula.key}`}
                            />
                            <span className="font-medium text-sm">{formula.label}</span>
                          </div>
                          <span className="text-xs text-gray-500 mt-1 ml-5">{formula.description}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Supported Shapes */}
                  <div>
                    <label className="block text-sm font-medium text-orange-700 mb-2">Supported Shapes (optional)</label>
                    <p className="text-xs text-orange-600 mb-2">Select additional shapes this template supports</p>
                    <div className="flex flex-wrap gap-2">
                      {FORMULA_TYPES.map((formula) => (
                        <label
                          key={formula.key}
                          className={`flex items-center gap-2 px-3 py-1.5 border rounded-full cursor-pointer text-sm ${
                            formData.supportedShapes.includes(formula.key)
                              ? 'bg-orange-500 text-white border-orange-500'
                              : 'bg-white text-gray-700 border-gray-300 hover:border-orange-300'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={formData.supportedShapes.includes(formula.key)}
                            onChange={() => toggleSupportedShape(formula.key)}
                            className="hidden"
                          />
                          {formula.label}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

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
                          onChange={(e) => updateField(index, { 
                            label: e.target.value, 
                            key: e.target.value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
                          })}
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
                    <p className="text-sm text-gray-500 text-center py-4">
                      {formData.templateType === 'raw_material' 
                        ? 'Select a formula type above to auto-populate fields, or add fields manually.'
                        : 'No fields added. Click "Add Field" to start.'}
                    </p>
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
                data-testid="save-template-btn"
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
