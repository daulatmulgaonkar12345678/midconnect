'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
  Beaker,
  Plus,
  Edit2,
  Trash2,
  Save,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowLeft,
  Scale,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

// Shape types for materials
const SHAPE_TYPES = [
  { value: 'circular_bar', label: 'Circular Bar / Round Bar' },
  { value: 'hollow_pipe', label: 'Hollow Pipe / Tube' },
  { value: 'square_bar', label: 'Square Bar' },
  { value: 'rectangular_bar', label: 'Rectangular Bar / Flat Bar' },
  { value: 'hexagonal_bar', label: 'Hexagonal Bar' },
  { value: 'sheet', label: 'Sheet / Plate' },
  { value: 'angle', label: 'Angle' },
  { value: 'channel', label: 'Channel' },
  { value: 'beam', label: 'I-Beam / H-Beam' },
];

interface Material {
  _id: string;
  name: string;
  material_family: string;
  shape_type?: string;
  linked_product_slug?: string;
  calculator_id?: string;
  density?: number;
  weight_per_unit?: Record<string, number>;
  description?: string;
  is_active?: boolean;
}

interface Calculator {
  _id: string;
  name: string;
  slug: string;
}

interface WeightPerUnitEntry {
  key: string;
  value: number;
}

interface MaterialFamily {
  name: string;
  count: number;
}

export default function MaterialsManagerPage() {
  const router = useRouter();
  const { user, getIdToken } = useAuth();
  
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialFamilies, setMaterialFamilies] = useState<string[]>([]);
  const [calculators, setCalculators] = useState<Calculator[]>([]);
  const [newFamily, setNewFamily] = useState('');
  const [showNewFamilyInput, setShowNewFamilyInput] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Form states
  const [showForm, setShowForm] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<Material | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    material_family: '',
    shape_type: '',
    linked_product_slug: '',
    calculator_id: '',
    density: '',
    description: ''
  });
  const [weightPerUnit, setWeightPerUnit] = useState<WeightPerUnitEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [showWeightSection, setShowWeightSection] = useState(false);
  
  // Delete confirmation
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Load materials
  useEffect(() => {
    loadMaterials();
  }, []);

  const loadMaterials = async () => {
    try {
      const [materialsRes, familiesRes, calculatorsRes] = await Promise.all([
        fetch(`${API_URL}/api/calculator/materials`),
        fetch(`${API_URL}/api/calculator/materials/families`),
        fetch(`${API_URL}/api/calculator/calculators`)
      ]);
      
      const materialsData = materialsRes.ok ? await materialsRes.json() : [];
      const familiesData = familiesRes.ok ? await familiesRes.json() : [];
      const calculatorsData = calculatorsRes.ok ? await calculatorsRes.json() : [];
      
      // Map materials to include new fields
      const mappedMaterials = materialsData.map((mat: any) => ({
        _id: mat._id,
        name: mat.name,
        material_family: mat.material_family || mat.material_type || 'General',
        shape_type: mat.shape_type,
        linked_product_slug: mat.linked_product_slug,
        calculator_id: mat.calculator_id,
        density: mat.density,
        weight_per_unit: mat.weight_per_unit || {},
        description: mat.description,
        is_active: mat.is_active !== false && mat.isActive !== false
      }));
      
      setMaterials(mappedMaterials);
      setCalculators(calculatorsData);
      
      // Set families from API or extract from materials
      if (familiesData.length > 0) {
        setMaterialFamilies(familiesData);
      } else {
        // Extract unique families from materials
        const uniqueFamilies = [...new Set(mappedMaterials.map((m: Material) => m.material_family).filter(Boolean))] as string[];
        setMaterialFamilies(uniqueFamilies.length > 0 ? uniqueFamilies : ['Steel', 'Stainless Steel', 'Aluminum']);
      }
    } catch (err) {
      setError('Failed to load materials');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    if (!formData.name.trim()) {
      setError('Material name is required');
      return;
    }
    
    if (!formData.material_family) {
      setError('Material family is required');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const token = await getIdToken();
      
      // Build weight_per_unit object
      const weightObj: Record<string, number> = {};
      weightPerUnit.forEach(entry => {
        if (entry.key && entry.value > 0) {
          weightObj[entry.key] = entry.value;
        }
      });
      
      // Auto-generate linked_product_slug from name if not provided
      const slug = formData.linked_product_slug || formData.name.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
      
      const payload = {
        name: formData.name.trim(),
        material_family: formData.material_family,
        shape_type: formData.shape_type || undefined,
        linked_product_slug: slug,
        calculator_id: formData.calculator_id || undefined,
        density: formData.density ? parseFloat(formData.density) : undefined,
        weight_per_unit: Object.keys(weightObj).length > 0 ? weightObj : undefined,
        description: formData.description || undefined
      };
      
      const url = editingMaterial 
        ? `${API_URL}/api/calculator/materials/${editingMaterial._id}`
        : `${API_URL}/api/calculator/materials`;
      
      const res = await fetch(url, {
        method: editingMaterial ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save material');
      }
      
      setSuccess(editingMaterial ? 'Material updated successfully' : 'Material created successfully');
      resetForm();
      loadMaterials();
    } catch (err: any) {
      setError(err.message || 'Failed to save material');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (material: Material) => {
    setEditingMaterial(material);
    setFormData({
      name: material.name,
      material_family: material.material_family || '',
      shape_type: material.shape_type || '',
      linked_product_slug: material.linked_product_slug || '',
      calculator_id: material.calculator_id || '',
      density: material.density?.toString() || '',
      description: material.description || ''
    });
    
    // Convert weight_per_unit object to array
    const entries = Object.entries(material.weight_per_unit || {}).map(([key, value]) => ({
      key,
      value
    }));
    setWeightPerUnit(entries);
    setShowWeightSection(entries.length > 0);
    setShowForm(true);
    setShowNewFamilyInput(false);
    setNewFamily('');
    setError('');
    setSuccess('');
  };

  const handleDelete = async (id: string) => {
    if (deletingId !== id) {
      setDeletingId(id);
      return;
    }
    
    try {
      const token = await getIdToken();
      const res = await fetch(`${API_URL}/api/calculator/materials/${id}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      
      if (!res.ok) throw new Error('Failed to delete');
      
      setSuccess('Material deleted');
      setDeletingId(null);
      loadMaterials();
    } catch (err) {
      setError('Failed to delete material');
    }
  };

  const resetForm = () => {
    setShowForm(false);
    setEditingMaterial(null);
    setFormData({ 
      name: '', 
      material_family: materialFamilies[0] || '', 
      shape_type: '',
      linked_product_slug: '',
      calculator_id: '',
      density: '', 
      description: '' 
    });
    setWeightPerUnit([]);
    setShowWeightSection(false);
    setShowNewFamilyInput(false);
    setNewFamily('');
    setError('');
  };

  const handleAddNewFamily = () => {
    if (newFamily.trim()) {
      const familyName = newFamily.trim();
      if (!materialFamilies.includes(familyName)) {
        setMaterialFamilies([...materialFamilies, familyName]);
      }
      setFormData(prev => ({ ...prev, material_family: familyName }));
      setNewFamily('');
      setShowNewFamilyInput(false);
    }
  };

  const addWeightEntry = () => {
    setWeightPerUnit([...weightPerUnit, { key: '', value: 0 }]);
  };

  const updateWeightEntry = (index: number, field: 'key' | 'value', val: string) => {
    const updated = [...weightPerUnit];
    if (field === 'key') {
      updated[index].key = val.toLowerCase().replace(/[^a-z0-9_]/g, '_');
    } else {
      updated[index].value = parseFloat(val) || 0;
    }
    setWeightPerUnit(updated);
  };

  const removeWeightEntry = (index: number) => {
    setWeightPerUnit(weightPerUnit.filter((_, i) => i !== index));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/admin')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Admin
          </button>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-xl">
                <Beaker className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Materials Manager</h1>
                <p className="text-gray-500">Manage materials, densities, and weight per unit</p>
              </div>
            </div>
            
            {!showForm && (
              <button
                onClick={() => { setShowForm(true); setEditingMaterial(null); setError(''); setSuccess(''); }}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Add Material
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            {error}
            <button onClick={() => setError('')} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}
        
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center gap-2">
            <CheckCircle className="h-5 w-5" />
            {success}
            <button onClick={() => setSuccess('')} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}

        {/* Add/Edit Form */}
        {showForm && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingMaterial ? 'Edit Material' : 'Add New Material'}
              </h2>
              <button onClick={resetForm} className="text-gray-500 hover:text-gray-700">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Material Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., MS Steel, SS316"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Material Family <span className="text-red-500">*</span>
                  </label>
                  {showNewFamilyInput ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newFamily}
                        onChange={(e) => setNewFamily(e.target.value)}
                        placeholder="Enter new family name"
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={handleAddNewFamily}
                        className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => { setShowNewFamilyInput(false); setNewFamily(''); }}
                        className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <select
                        value={formData.material_family}
                        onChange={(e) => setFormData(prev => ({ ...prev, material_family: e.target.value }))}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                      >
                        <option value="">-- Select Family --</option>
                        {materialFamilies.map(family => (
                          <option key={family} value={family}>
                            {family}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setShowNewFamilyInput(true)}
                        className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 flex items-center gap-1"
                        title="Add new family"
                      >
                        <Plus className="h-4 w-4" />
                        New
                      </button>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Group materials by family (e.g., Steel, Stainless Steel, Aluminum)
                  </p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Shape Type
                  </label>
                  <select
                    value={formData.shape_type}
                    onChange={(e) => setFormData(prev => ({ ...prev, shape_type: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">-- Select Shape --</option>
                    {SHAPE_TYPES.map(shape => (
                      <option key={shape.value} value={shape.value}>
                        {shape.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Determines which calculator formula to use</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Linked Calculator
                  </label>
                  <select
                    value={formData.calculator_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, calculator_id: e.target.value }))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">-- Select Calculator --</option>
                    {calculators.map(calc => (
                      <option key={calc._id} value={calc._id}>
                        {calc.name}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Calculator used for weight calculation</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Density (kg/m³)
                  </label>
                  <input
                    type="number"
                    value={formData.density}
                    onChange={(e) => setFormData(prev => ({ ...prev, density: e.target.value }))}
                    placeholder="e.g., 7850"
                    step="0.01"
                    min="0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Used for volume-to-weight calculations</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Optional description"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
              
              {/* Weight Per Unit Section */}
              <div className="border rounded-lg">
                <button
                  type="button"
                  onClick={() => setShowWeightSection(!showWeightSection)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 rounded-t-lg"
                >
                  <div className="flex items-center gap-2">
                    <Scale className="h-4 w-4 text-gray-600" />
                    <span className="font-medium text-gray-700">Weight Per Unit (Optional)</span>
                    {weightPerUnit.length > 0 && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                        {weightPerUnit.length} entries
                      </span>
                    )}
                  </div>
                  {showWeightSection ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
                
                {showWeightSection && (
                  <div className="p-4 space-y-3">
                    <p className="text-sm text-gray-600">
                      Add pre-calculated weights for common sizes. Example: "10mm_round_per_meter" = 0.617 kg
                    </p>
                    
                    {weightPerUnit.map((entry, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <input
                          type="text"
                          value={entry.key}
                          onChange={(e) => updateWeightEntry(index, 'key', e.target.value)}
                          placeholder="e.g., 10mm_round_per_meter"
                          className="flex-1 px-3 py-2 border rounded-lg text-sm"
                        />
                        <input
                          type="number"
                          step="any"
                          value={entry.value || ''}
                          onChange={(e) => updateWeightEntry(index, 'value', e.target.value)}
                          placeholder="kg"
                          className="w-32 px-3 py-2 border rounded-lg text-sm"
                        />
                        <span className="text-sm text-gray-500">kg</span>
                        <button
                          type="button"
                          onClick={() => removeWeightEntry(index)}
                          className="p-1 text-red-500 hover:bg-red-50 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                    
                    <button
                      type="button"
                      onClick={addWeightEntry}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg"
                    >
                      <Plus className="h-4 w-4" />
                      Add Weight Entry
                    </button>
                  </div>
                )}
              </div>
              
              {/* Form Actions */}
              <div className="flex items-center gap-3 pt-4">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {editingMaterial ? 'Update Material' : 'Create Material'}
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Materials List */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="p-4 border-b">
            <h2 className="font-semibold">All Materials ({materials.length})</h2>
          </div>
          
          {materials.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Beaker className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No materials found</p>
              <p className="text-sm">Add your first material to get started</p>
            </div>
          ) : (
            <div className="divide-y">
              {materials.map(material => {
                const linkedCalc = calculators.find(c => c._id === material.calculator_id);
                const shapeLabel = SHAPE_TYPES.find(s => s.value === material.shape_type)?.label;
                
                return (
                <div key={material._id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-medium">{material.name}</h3>
                        <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded font-medium">
                          {material.material_family}
                        </span>
                        {shapeLabel && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded font-medium">
                            {shapeLabel}
                          </span>
                        )}
                        {linkedCalc && (
                          <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded font-medium">
                            🧮 {linkedCalc.name}
                          </span>
                        )}
                        {material.is_active === false && (
                          <span className="px-2 py-0.5 bg-red-100 text-red-600 text-xs rounded">
                            Inactive
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                        {material.density && (
                          <span>Density: {material.density.toLocaleString()} kg/m³</span>
                        )}
                        {material.weight_per_unit && Object.keys(material.weight_per_unit).length > 0 && (
                          <span>{Object.keys(material.weight_per_unit).length} weight entries</span>
                        )}
                      </div>
                      
                      {material.description && (
                        <p className="text-sm text-gray-400 mt-1">{material.description}</p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleEdit(material)}
                        className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(material._id)}
                        className={`p-2 rounded ${
                          deletingId === material._id 
                            ? 'text-white bg-red-600 hover:bg-red-700' 
                            : 'text-gray-500 hover:text-red-600 hover:bg-red-50'
                        }`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
