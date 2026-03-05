'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Plus, Edit2, Trash2, Loader2, X, Check, AlertTriangle, Eye, EyeOff, GripVertical, Box, Circle, Square, Layers } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface ShapeField {
  key: string;
  label: string;
  unit_options: string[];
  default_unit: string;
  required: boolean;
}

interface Shape {
  _id: string;
  key: string;
  name: string;
  description?: string;
  icon?: string;
  fields: ShapeField[];
  formula: string;
  formula_type: string;
  isActive: boolean;
  createdAt?: string;
  updatedAt?: string;
}

const FORMULA_TYPES = [
  { value: 'round_bar', label: 'Round Bar (Solid Cylinder)', formula: 'V = π × (d/2)² × L' },
  { value: 'square_bar', label: 'Square Bar', formula: 'V = side² × L' },
  { value: 'rectangular_bar', label: 'Rectangular Bar', formula: 'V = width × height × L' },
  { value: 'pipe', label: 'Pipe/Tube (Hollow Cylinder)', formula: 'V = π × ((OD/2)² - (ID/2)²) × L' },
  { value: 'square_pipe', label: 'Square Pipe/Tube', formula: 'V = (outer² - inner²) × L' },
  { value: 'plate', label: 'Plate/Sheet', formula: 'V = thickness × width × L' },
  { value: 'hexagonal_bar', label: 'Hexagonal Bar', formula: 'V = (3√3/2) × side² × L' },
  { value: 'angle', label: 'Angle (L-Shape)', formula: 'V = thickness × (w1 + w2 - thickness) × L' },
  { value: 'channel', label: 'Channel (C-Shape)', formula: 'V = thickness × (web + 2×flange - 2×t) × L' },
];

const UNIT_OPTIONS = {
  length: ['mm', 'cm', 'meter', 'inch', 'feet'],
  dimension: ['mm', 'cm', 'inch'],
};

export default function AdminShapesPage() {
  const { getIdToken } = useAuth();
  const [shapes, setShapes] = useState<Shape[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingShape, setEditingShape] = useState<Shape | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    key: '',
    name: '',
    description: '',
    icon: 'box',
    fields: [] as ShapeField[],
    formula: '',
    formula_type: 'round_bar'
  });

  useEffect(() => {
    fetchShapes();
  }, []);

  const fetchShapes = async () => {
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const res = await fetch(`${API_URL}/api/raw-materials/admin/shapes`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Failed to load shapes');
      const data = await res.json();
      setShapes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load shapes');
    } finally {
      setIsLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingShape(null);
    setFormData({
      key: '',
      name: '',
      description: '',
      icon: 'box',
      fields: [
        { key: 'diameter', label: 'Diameter', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
        { key: 'length', label: 'Length', unit_options: ['mm', 'cm', 'meter', 'inch', 'feet'], default_unit: 'meter', required: true }
      ],
      formula: 'V = π × (d/2)² × L',
      formula_type: 'round_bar'
    });
    setShowModal(true);
    setError(null);
  };

  const openEditModal = (shape: Shape) => {
    setEditingShape(shape);
    setFormData({
      key: shape.key,
      name: shape.name,
      description: shape.description || '',
      icon: shape.icon || 'box',
      fields: shape.fields || [],
      formula: shape.formula || '',
      formula_type: shape.formula_type || 'round_bar'
    });
    setShowModal(true);
    setError(null);
  };

  const addField = () => {
    setFormData({
      ...formData,
      fields: [
        ...formData.fields,
        { key: '', label: '', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true }
      ]
    });
  };

  const updateField = (index: number, updates: Partial<ShapeField>) => {
    const newFields = [...formData.fields];
    newFields[index] = { ...newFields[index], ...updates };
    
    // Auto-generate key from label
    if (updates.label && !newFields[index].key) {
      newFields[index].key = updates.label.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    }
    
    setFormData({ ...formData, fields: newFields });
  };

  const removeField = (index: number) => {
    setFormData({
      ...formData,
      fields: formData.fields.filter((_, i) => i !== index)
    });
  };

  const applyFormulaTemplate = (formulaType: string) => {
    const template = FORMULA_TYPES.find(f => f.value === formulaType);
    if (!template) return;
    
    let fields: ShapeField[] = [];
    
    switch (formulaType) {
      case 'round_bar':
        fields = [
          { key: 'diameter', label: 'Diameter', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'square_bar':
        fields = [
          { key: 'side', label: 'Side', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'rectangular_bar':
        fields = [
          { key: 'width', label: 'Width', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'height', label: 'Height', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'pipe':
        fields = [
          { key: 'outer_diameter', label: 'Outer Diameter (OD)', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'thickness', label: 'Wall Thickness', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'square_pipe':
        fields = [
          { key: 'outer_side', label: 'Outer Side', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'thickness', label: 'Wall Thickness', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'plate':
        fields = [
          { key: 'thickness', label: 'Thickness', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'width', label: 'Width', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'hexagonal_bar':
        fields = [
          { key: 'side', label: 'Hexagon Side', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'angle':
        fields = [
          { key: 'width1', label: 'Width 1', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'width2', label: 'Width 2', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'thickness', label: 'Thickness', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
      case 'channel':
        fields = [
          { key: 'web', label: 'Web Height', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'flange', label: 'Flange Width', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'thickness', label: 'Thickness', unit_options: UNIT_OPTIONS.dimension, default_unit: 'mm', required: true },
          { key: 'length', label: 'Length', unit_options: UNIT_OPTIONS.length, default_unit: 'meter', required: true }
        ];
        break;
    }
    
    setFormData({
      ...formData,
      formula_type: formulaType,
      formula: template.formula,
      fields
    });
  };

  const handleSave = async () => {
    if (!formData.key.trim()) {
      setError('Shape key is required');
      return;
    }
    if (!formData.name.trim()) {
      setError('Shape name is required');
      return;
    }
    if (formData.fields.length === 0) {
      setError('At least one field is required');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const payload = {
        key: formData.key.toLowerCase().replace(/\s+/g, '_'),
        name: formData.name,
        description: formData.description || null,
        icon: formData.icon || 'box',
        fields: formData.fields,
        formula: formData.formula,
        formula_type: formData.formula_type
      };

      const url = editingShape 
        ? `${API_URL}/api/raw-materials/admin/shapes/${editingShape._id}`
        : `${API_URL}/api/raw-materials/admin/shapes`;
      
      const res = await fetch(url, {
        method: editingShape ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save shape');
      }

      setShowModal(false);
      fetchShapes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save shape');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (shape: Shape) => {
    try {
      const token = await getIdToken();
      if (!token) return;
      
      const res = await fetch(`${API_URL}/api/raw-materials/admin/shapes/${shape._id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ isActive: !shape.isActive })
      });
      
      if (!res.ok) throw new Error('Failed to update');
      fetchShapes();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update');
    }
  };

  const handleDelete = async (shape: Shape) => {
    if (!confirm(`Delete shape "${shape.name}"?`)) return;

    try {
      const token = await getIdToken();
      if (!token) return;
      
      const res = await fetch(`${API_URL}/api/raw-materials/admin/shapes/${shape._id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Failed to delete');
      fetchShapes();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete');
    }
  };

  const getShapeIcon = (iconName?: string) => {
    switch (iconName) {
      case 'circle': return <Circle className="h-5 w-5" />;
      case 'square': return <Square className="h-5 w-5" />;
      case 'layers': return <Layers className="h-5 w-5" />;
      default: return <Box className="h-5 w-5" />;
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
          <h1 className="text-2xl font-bold text-gray-900">Shape Configurations</h1>
          <p className="text-gray-500">Define shapes and their dimension fields for weight calculation</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          data-testid="add-shape-btn"
        >
          <Plus className="h-5 w-5" /> Add Shape
        </button>
      </div>

      {/* Shapes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {shapes.map((shape) => (
          <div 
            key={shape._id} 
            className={`bg-white rounded-xl shadow-sm p-6 border-2 ${
              !shape.isActive ? 'opacity-60 border-gray-200' : 'border-blue-100'
            }`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg text-blue-600">
                  {getShapeIcon(shape.icon)}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{shape.name}</h3>
                  <p className="text-xs text-gray-500 font-mono">{shape.key}</p>
                </div>
              </div>
              <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                shape.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {shape.isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
            
            {/* Formula */}
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 mb-1">Formula</p>
              <code className="text-sm text-blue-600">{shape.formula}</code>
            </div>
            
            {/* Fields */}
            <div className="mb-4">
              <p className="text-xs text-gray-500 uppercase mb-2">Fields ({shape.fields?.length || 0})</p>
              <div className="flex flex-wrap gap-2">
                {shape.fields?.map((field) => (
                  <span key={field.key} className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full">
                    {field.label} ({field.default_unit})
                  </span>
                ))}
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex items-center gap-2 pt-4 border-t">
              <button
                onClick={() => handleToggleActive(shape)}
                className="p-2 text-gray-400 hover:text-gray-600 transition"
                title={shape.isActive ? 'Deactivate' : 'Activate'}
              >
                {shape.isActive ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
              <button
                onClick={() => openEditModal(shape)}
                className="p-2 text-gray-400 hover:text-blue-600 transition"
              >
                <Edit2 className="h-4 w-4" />
              </button>
              <button
                onClick={() => handleDelete(shape)}
                className="p-2 text-gray-400 hover:text-red-600 transition"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
        {shapes.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            No shapes configured yet. Click "Add Shape" to create one.
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-white rounded-xl p-6 w-full max-w-3xl my-8 mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{editingShape ? 'Edit Shape' : 'Create Shape'}</h2>
              <button onClick={() => setShowModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="h-5 w-5" />
              </button>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> {error}
              </div>
            )}

            <div className="space-y-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Key *</label>
                  <input
                    type="text"
                    value={formData.key}
                    onChange={(e) => setFormData({ ...formData, key: e.target.value.toLowerCase().replace(/\s+/g, '_') })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., round_bar"
                    disabled={!!editingShape}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Round Bar"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Solid circular bar"
                />
              </div>

              {/* Formula Type Template */}
              <div className="p-4 bg-blue-50 rounded-lg">
                <label className="block text-sm font-medium text-blue-700 mb-2">Formula Template</label>
                <select
                  value={formData.formula_type}
                  onChange={(e) => applyFormulaTemplate(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  {FORMULA_TYPES.map((f) => (
                    <option key={f.value} value={f.value}>{f.label} - {f.formula}</option>
                  ))}
                </select>
                <p className="text-xs text-blue-600 mt-2">
                  Selecting a template will auto-populate the fields. You can customize them below.
                </p>
              </div>

              {/* Formula Display */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Formula</label>
                <input
                  type="text"
                  value={formData.formula}
                  onChange={(e) => setFormData({ ...formData, formula: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono"
                  placeholder="e.g., V = π × (d/2)² × L"
                />
              </div>

              {/* Fields */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-700">Dimension Fields *</label>
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
                      <div className="flex-1 grid grid-cols-4 gap-2">
                        <input
                          type="text"
                          value={field.label}
                          onChange={(e) => updateField(index, { label: e.target.value })}
                          className="px-2 py-1.5 border rounded text-sm"
                          placeholder="Label"
                        />
                        <input
                          type="text"
                          value={field.key}
                          onChange={(e) => updateField(index, { key: e.target.value })}
                          className="px-2 py-1.5 border rounded text-sm font-mono"
                          placeholder="key"
                        />
                        <select
                          value={field.default_unit}
                          onChange={(e) => updateField(index, { default_unit: e.target.value })}
                          className="px-2 py-1.5 border rounded text-sm"
                        >
                          {field.unit_options.map((u) => (
                            <option key={u} value={u}>{u}</option>
                          ))}
                        </select>
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
                      Select a formula template above to auto-populate fields.
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
              >
                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                {editingShape ? 'Update' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
