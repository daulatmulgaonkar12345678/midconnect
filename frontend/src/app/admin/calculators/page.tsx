'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Calculator,
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  ChevronDown,
  ChevronUp,
  GripVertical,
  AlertCircle,
  CheckCircle,
  Info,
  Loader2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

// ============================================================================
// TYPES
// ============================================================================

interface UnitDefinition {
  key: string;
  label: string;
  conversion_to_base: number;
}

interface UnitGroup {
  _id: string;
  name: string;
  display_name: string;
  base_unit: string;
  units: UnitDefinition[];
}

interface CalculatorField {
  key: string;
  label: string;
  unit_group: string;
  default_unit: string;
  required: boolean;
  order: number;
  placeholder?: string;
  help_text?: string;
}

interface MaterialFormulaOverride {
  material_ids: string[];
  formula_expression: string;
  fields?: CalculatorField[];
  description?: string;
}

interface CalculatorTemplate {
  _id?: string;
  name: string;
  slug: string;
  category_id?: string;
  description?: string;
  fields: CalculatorField[];
  formula_expression: string;
  material_formulas?: MaterialFormulaOverride[];
  output_unit: string;
  output_label: string;
  material_family?: string;
  use_material_density: boolean;
  icon?: string;
  is_active?: boolean;
}

interface Material {
  _id: string;
  name: string;
  material_family?: string;
  density?: number;
}

interface Category {
  _id: string;
  name: string;
}

// ============================================================================
// FORMULA HELPER
// ============================================================================

const FORMULA_EXAMPLES = [
  { name: 'Round Bar', formula: 'pi * pow(diameter / 2, 2) * length * density', vars: 'diameter, length, density' },
  { name: 'Square Bar', formula: 'pow(side, 2) * length * density', vars: 'side, length, density' },
  { name: 'Hex Bar', formula: '0.866 * pow(across_flats, 2) * length * density', vars: 'across_flats, length, density' },
  { name: 'Pipe', formula: 'pi * (pow(outer_diameter / 2, 2) - pow((outer_diameter - 2 * thickness) / 2, 2)) * length * density', vars: 'outer_diameter, thickness, length, density' },
  { name: 'Plate/Sheet', formula: 'thickness * width * length * density', vars: 'thickness, width, length, density' },
  { name: 'Angle', formula: 'thickness * (leg_a + leg_b - thickness) * length * density', vars: 'leg_a, leg_b, thickness, length, density' },
  { name: 'Channel', formula: '((web_height - 2 * flange_thickness) * web_thickness + 2 * flange_width * flange_thickness) * length * density', vars: 'web_height, flange_width, web_thickness, flange_thickness, length, density' },
  { name: 'I-Beam/H-Beam', formula: '(2 * flange_width * flange_thickness + (height - 2 * flange_thickness) * web_thickness) * length * density', vars: 'height, flange_width, web_thickness, flange_thickness, length, density' },
];

const FORMULA_FUNCTIONS = [
  { name: 'pi', desc: 'π (3.14159...)' },
  { name: 'pow(x, n)', desc: 'x raised to power n' },
  { name: 'sqrt(x)', desc: 'Square root of x' },
  { name: 'abs(x)', desc: 'Absolute value' },
  { name: 'round(x)', desc: 'Round to nearest integer' },
  { name: 'floor(x)', desc: 'Round down' },
  { name: 'ceil(x)', desc: 'Round up' },
  { name: 'min(a, b)', desc: 'Minimum of a and b' },
  { name: 'max(a, b)', desc: 'Maximum of a and b' },
];

// ============================================================================
// COMPONENTS
// ============================================================================

function FormulaHelperPanel({ onInsert }: { onInsert: (text: string) => void }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-blue-700 font-medium w-full"
      >
        <Info className="h-4 w-4" />
        Formula Helper
        {isOpen ? <ChevronUp className="h-4 w-4 ml-auto" /> : <ChevronDown className="h-4 w-4 ml-auto" />}
      </button>
      
      {isOpen && (
        <div className="mt-4 space-y-4">
          <div>
            <h4 className="font-medium text-sm mb-2">Available Functions:</h4>
            <div className="flex flex-wrap gap-2">
              {FORMULA_FUNCTIONS.map(fn => (
                <button
                  key={fn.name}
                  type="button"
                  onClick={() => onInsert(fn.name.includes('(') ? fn.name : `${fn.name}`)}
                  className="px-2 py-1 bg-white border rounded text-xs hover:bg-blue-100"
                  title={fn.desc}
                >
                  {fn.name}
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <h4 className="font-medium text-sm mb-2">Example Formulas:</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {FORMULA_EXAMPLES.map(ex => (
                <div key={ex.name} className="bg-white p-2 rounded border text-xs">
                  <div className="font-medium">{ex.name}</div>
                  <code className="text-blue-600 block mt-1 break-all">{ex.formula}</code>
                  <div className="text-gray-500 mt-1">Variables: {ex.vars}</div>
                  <button
                    type="button"
                    onClick={() => onInsert(ex.formula)}
                    className="text-blue-600 hover:underline mt-1"
                  >
                    Use this formula
                  </button>
                </div>
              ))}
            </div>
          </div>
          
          <div className="text-xs text-gray-600">
            <strong>Note:</strong> Use <code>density</code> or <code>material_density</code> for material density (kg/m³).
            All length dimensions are converted to meters before formula evaluation.
          </div>
        </div>
      )}
    </div>
  );
}

function FieldEditor({
  field,
  unitGroups,
  onChange,
  onRemove,
  index
}: {
  field: CalculatorField;
  unitGroups: UnitGroup[];
  onChange: (field: CalculatorField) => void;
  onRemove: () => void;
  index: number;
}) {
  const selectedGroup = unitGroups.find(g => g.name === field.unit_group);

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border">
      <div className="text-gray-400 cursor-move">
        <GripVertical className="h-5 w-5" />
      </div>
      
      <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs font-medium text-gray-600">Field Key</label>
          <input
            type="text"
            value={field.key}
            onChange={(e) => onChange({ ...field, key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_') })}
            className="w-full px-2 py-1 border rounded text-sm"
            placeholder="e.g., diameter"
          />
        </div>
        
        <div>
          <label className="text-xs font-medium text-gray-600">Label</label>
          <input
            type="text"
            value={field.label}
            onChange={(e) => onChange({ ...field, label: e.target.value })}
            className="w-full px-2 py-1 border rounded text-sm"
            placeholder="e.g., Diameter"
          />
        </div>
        
        <div>
          <label className="text-xs font-medium text-gray-600">Unit Group</label>
          <select
            value={field.unit_group}
            onChange={(e) => {
              const newGroup = unitGroups.find(g => g.name === e.target.value);
              onChange({
                ...field,
                unit_group: e.target.value,
                default_unit: newGroup?.base_unit || ''
              });
            }}
            className="w-full px-2 py-1 border rounded text-sm"
          >
            <option value="">Select...</option>
            {unitGroups.map(g => (
              <option key={g.name} value={g.name}>{g.display_name}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="text-xs font-medium text-gray-600">Default Unit</label>
          <select
            value={field.default_unit}
            onChange={(e) => onChange({ ...field, default_unit: e.target.value })}
            className="w-full px-2 py-1 border rounded text-sm"
            disabled={!selectedGroup}
          >
            <option value="">Select...</option>
            {selectedGroup?.units.map(u => (
              <option key={u.key} value={u.key}>{u.label}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-xs">
          <input
            type="checkbox"
            checked={field.required}
            onChange={(e) => onChange({ ...field, required: e.target.checked })}
          />
          Required
        </label>
        
        <button
          type="button"
          onClick={onRemove}
          className="p-1 text-red-500 hover:bg-red-50 rounded"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN PAGE
// ============================================================================

export default function AdminCalculatorsPage() {
  const router = useRouter();
  
  // State
  const [calculators, setCalculators] = useState<CalculatorTemplate[]>([]);
  const [unitGroups, setUnitGroups] = useState<UnitGroup[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [materialFamilies, setMaterialFamilies] = useState<string[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Editor state
  const [isEditing, setIsEditing] = useState(false);
  const [editingCalc, setEditingCalc] = useState<CalculatorTemplate | null>(null);
  const [showMaterialFormulas, setShowMaterialFormulas] = useState(false);
  
  // Load data
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    setLoading(true);
    try {
      const [calcsRes, unitsRes, catsRes, familiesRes, materialsRes] = await Promise.all([
        fetch(`${API_URL}/api/calculator/calculators`),
        fetch(`${API_URL}/api/calculator/unit-groups`),
        fetch(`${API_URL}/api/categories/all`),
        fetch(`${API_URL}/api/calculator/materials/families`),
        fetch(`${API_URL}/api/calculator/materials`)
      ]);
      
      if (calcsRes.ok) setCalculators(await calcsRes.json());
      if (unitsRes.ok) setUnitGroups(await unitsRes.json());
      if (catsRes.ok) setCategories(await catsRes.json());
      if (familiesRes.ok) setMaterialFamilies(await familiesRes.json());
      if (materialsRes.ok) setMaterials(await materialsRes.json());
    } catch (err) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };
  
  const handleNewCalculator = () => {
    setEditingCalc({
      name: '',
      slug: '',
      description: '',
      fields: [],
      formula_expression: '',
      material_formulas: [],
      output_unit: 'kg',
      output_label: 'Weight',
      use_material_density: true,
    });
    setShowMaterialFormulas(false);
    setIsEditing(true);
  };
  
  const handleEditCalculator = (calc: CalculatorTemplate) => {
    setEditingCalc({ ...calc, material_formulas: calc.material_formulas || [] });
    setShowMaterialFormulas((calc.material_formulas?.length || 0) > 0);
    setIsEditing(true);
  };
  
  const handleDeleteCalculator = async (id: string) => {
    if (!confirm('Are you sure you want to delete this calculator?')) return;
    
    try {
      const res = await fetch(`${API_URL}/api/calculator/calculators/${id}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        setSuccess('Calculator deleted');
        loadData();
      } else {
        setError('Failed to delete calculator');
      }
    } catch (err) {
      setError('Failed to delete calculator');
    }
  };
  
  const handleSaveCalculator = async () => {
    if (!editingCalc) return;
    
    // Validate
    if (!editingCalc.name || !editingCalc.slug || !editingCalc.formula_expression) {
      setError('Please fill in all required fields');
      return;
    }
    
    if (editingCalc.fields.length === 0) {
      setError('Please add at least one field');
      return;
    }
    
    setSaving(true);
    setError(null);
    
    try {
      const isNew = !editingCalc._id;
      const url = isNew 
        ? `${API_URL}/api/calculator/calculators`
        : `${API_URL}/api/calculator/calculators/${editingCalc._id}`;
      
      // Clean up empty material formulas
      const payload = {
        ...editingCalc,
        material_formulas: editingCalc.material_formulas?.filter(
          mf => mf.material_ids.length > 0 && mf.formula_expression.trim()
        ) || []
      };
      
      const res = await fetch(url, {
        method: isNew ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        setSuccess(isNew ? 'Calculator created' : 'Calculator updated');
        setIsEditing(false);
        setEditingCalc(null);
        loadData();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to save calculator');
      }
    } catch (err) {
      setError('Failed to save calculator');
    } finally {
      setSaving(false);
    }
  };
  
  const handleAddField = () => {
    if (!editingCalc) return;
    
    const newField: CalculatorField = {
      key: `field_${editingCalc.fields.length + 1}`,
      label: 'New Field',
      unit_group: 'length',
      default_unit: 'mm',
      required: true,
      order: editingCalc.fields.length
    };
    
    setEditingCalc({
      ...editingCalc,
      fields: [...editingCalc.fields, newField]
    });
  };
  
  const handleUpdateField = (index: number, field: CalculatorField) => {
    if (!editingCalc) return;
    
    const newFields = [...editingCalc.fields];
    newFields[index] = field;
    setEditingCalc({ ...editingCalc, fields: newFields });
  };
  
  const handleRemoveField = (index: number) => {
    if (!editingCalc) return;
    
    const newFields = editingCalc.fields.filter((_, i) => i !== index);
    setEditingCalc({ ...editingCalc, fields: newFields });
  };
  
  const handleInsertFormula = (text: string) => {
    if (!editingCalc) return;
    setEditingCalc({ ...editingCalc, formula_expression: text });
  };
  
  // Material Formula Override Handlers
  const handleAddMaterialFormula = () => {
    if (!editingCalc) return;
    
    const newFormula: MaterialFormulaOverride = {
      material_ids: [],
      formula_expression: editingCalc.formula_expression || '', // Copy default formula
      description: ''
    };
    
    setEditingCalc({
      ...editingCalc,
      material_formulas: [...(editingCalc.material_formulas || []), newFormula]
    });
  };
  
  const handleUpdateMaterialFormula = (index: number, formula: MaterialFormulaOverride) => {
    if (!editingCalc) return;
    
    const newFormulas = [...(editingCalc.material_formulas || [])];
    newFormulas[index] = formula;
    setEditingCalc({ ...editingCalc, material_formulas: newFormulas });
  };
  
  const handleRemoveMaterialFormula = (index: number) => {
    if (!editingCalc) return;
    
    const newFormulas = (editingCalc.material_formulas || []).filter((_, i) => i !== index);
    setEditingCalc({ ...editingCalc, material_formulas: newFormulas });
  };
  
  const handleToggleMaterialInFormula = (formulaIndex: number, materialId: string) => {
    if (!editingCalc) return;
    
    const formulas = [...(editingCalc.material_formulas || [])];
    const formula = formulas[formulaIndex];
    
    if (formula.material_ids.includes(materialId)) {
      formula.material_ids = formula.material_ids.filter(id => id !== materialId);
    } else {
      formula.material_ids = [...formula.material_ids, materialId];
    }
    
    setEditingCalc({ ...editingCalc, material_formulas: formulas });
  };
  
  // Get materials filtered by current family
  const getFilteredMaterials = () => {
    if (!editingCalc?.material_family) return materials;
    return materials.filter(m => m.material_family === editingCalc.material_family);
  };
  
  // Auto-generate slug from name
  const handleNameChange = (name: string) => {
    if (!editingCalc) return;
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    setEditingCalc({ ...editingCalc, name, slug });
  };
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Calculator Templates</h1>
            <p className="text-gray-600">Create and manage configurable calculators</p>
          </div>
          
          {!isEditing && (
            <button
              onClick={handleNewCalculator}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              New Calculator
            </button>
          )}
        </div>
        
        {/* Alerts */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
            <CheckCircle className="h-5 w-5" />
            {success}
            <button onClick={() => setSuccess(null)} className="ml-auto">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}
        
        {/* Editor */}
        {isEditing && editingCalc && (
          <div className="bg-white rounded-xl shadow-sm border p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">
                {editingCalc._id ? 'Edit Calculator' : 'New Calculator'}
              </h2>
              <button
                onClick={() => { setIsEditing(false); setEditingCalc(null); }}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Calculator Name *</label>
                  <input
                    type="text"
                    value={editingCalc.name}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., Round Bar Calculator"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Slug *</label>
                  <input
                    type="text"
                    value={editingCalc.slug}
                    onChange={(e) => setEditingCalc({ ...editingCalc, slug: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., round-bar"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Linked Category</label>
                  <select
                    value={editingCalc.category_id || ''}
                    onChange={(e) => setEditingCalc({ ...editingCalc, category_id: e.target.value || undefined })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">None (Manual use only)</option>
                    {categories.map(cat => (
                      <option key={cat._id} value={cat._id}>{cat.name}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Material Family</label>
                  <select
                    value={editingCalc.material_family || ''}
                    onChange={(e) => setEditingCalc({ ...editingCalc, material_family: e.target.value || undefined })}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">All Materials</option>
                    {materialFamilies.map(family => (
                      <option key={family} value={family}>{family}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Filter materials shown in calculator dropdown</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Output Label</label>
                  <input
                    type="text"
                    value={editingCalc.output_label}
                    onChange={(e) => setEditingCalc({ ...editingCalc, output_label: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., Weight"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Output Unit</label>
                  <input
                    type="text"
                    value={editingCalc.output_unit}
                    onChange={(e) => setEditingCalc({ ...editingCalc, output_unit: e.target.value })}
                    className="w-full px-3 py-2 border rounded-lg"
                    placeholder="e.g., kg"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={editingCalc.description || ''}
                  onChange={(e) => setEditingCalc({ ...editingCalc, description: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  rows={2}
                  placeholder="Calculator description..."
                />
              </div>
              
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="useDensity"
                  checked={editingCalc.use_material_density}
                  onChange={(e) => setEditingCalc({ ...editingCalc, use_material_density: e.target.checked })}
                />
                <label htmlFor="useDensity" className="text-sm">
                  This calculator uses material density (show material selector)
                </label>
              </div>
              
              {/* Fields */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium">Calculator Fields</label>
                  <button
                    type="button"
                    onClick={handleAddField}
                    className="flex items-center gap-1 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded"
                  >
                    <Plus className="h-4 w-4" />
                    Add Field
                  </button>
                </div>
                
                <div className="space-y-2">
                  {editingCalc.fields.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed">
                      No fields yet. Click "Add Field" to create dimension inputs.
                    </div>
                  ) : (
                    editingCalc.fields.map((field, index) => (
                      <FieldEditor
                        key={index}
                        field={field}
                        unitGroups={unitGroups}
                        onChange={(f) => handleUpdateField(index, f)}
                        onRemove={() => handleRemoveField(index)}
                        index={index}
                      />
                    ))
                  )}
                </div>
              </div>
              
              {/* Formula */}
              <div>
                <label className="block text-sm font-medium mb-1">Default Formula Expression *</label>
                <textarea
                  value={editingCalc.formula_expression}
                  onChange={(e) => setEditingCalc({ ...editingCalc, formula_expression: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
                  rows={3}
                  placeholder="e.g., pi * pow(diameter / 2, 2) * length * density"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use field keys as variables. Available: {editingCalc.fields.map(f => f.key).join(', ')}
                  {editingCalc.use_material_density && ', density'}
                </p>
              </div>
              
              <FormulaHelperPanel onInsert={handleInsertFormula} />
              
              {/* Material-Specific Formulas */}
              {editingCalc.use_material_density && (
                <div className="border rounded-lg p-4 bg-amber-50">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <label className="block text-sm font-semibold text-amber-800">
                        Material-Specific Formulas (Optional)
                      </label>
                      <p className="text-xs text-amber-700 mt-0.5">
                        Override the default formula for specific materials (e.g., different formula for Hollow Pipe vs Solid Bar)
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleAddMaterialFormula}
                      className="flex items-center gap-1 px-3 py-1.5 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700"
                    >
                      <Plus className="h-4 w-4" />
                      Add Formula Override
                    </button>
                  </div>
                  
                  {(!editingCalc.material_formulas || editingCalc.material_formulas.length === 0) ? (
                    <div className="text-center py-6 text-amber-600 bg-amber-100/50 rounded-lg border-2 border-dashed border-amber-300">
                      <p className="font-medium">No material-specific formulas</p>
                      <p className="text-xs mt-1">All materials will use the default formula above</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {editingCalc.material_formulas.map((formula, index) => {
                        const filteredMaterials = getFilteredMaterials();
                        
                        return (
                          <div key={index} className="bg-white border border-amber-200 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start justify-between mb-3">
                              <div className="flex-1">
                                <input
                                  type="text"
                                  value={formula.description || ''}
                                  onChange={(e) => handleUpdateMaterialFormula(index, { ...formula, description: e.target.value })}
                                  className="w-full px-3 py-1.5 text-sm font-medium border rounded focus:ring-2 focus:ring-amber-500"
                                  placeholder="Formula name (e.g., Hollow Pipe, Solid Round Bar)"
                                />
                              </div>
                              <button
                                type="button"
                                onClick={() => handleRemoveMaterialFormula(index)}
                                className="ml-2 p-1.5 text-red-500 hover:bg-red-50 rounded"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                            
                            {/* Material Selection */}
                            <div className="mb-3">
                              <label className="block text-xs font-medium text-gray-600 mb-1.5">
                                Select Materials that use this formula:
                              </label>
                              <div className="flex flex-wrap gap-2 p-2 bg-gray-50 rounded-lg max-h-32 overflow-y-auto">
                                {filteredMaterials.length === 0 ? (
                                  <span className="text-xs text-gray-500 italic">
                                    {editingCalc.material_family 
                                      ? `No materials in "${editingCalc.material_family}" family` 
                                      : 'No materials available'}
                                  </span>
                                ) : (
                                  filteredMaterials.map(mat => (
                                    <button
                                      key={mat._id}
                                      type="button"
                                      onClick={() => handleToggleMaterialInFormula(index, mat._id)}
                                      className={`px-2 py-1 text-xs rounded-full border transition-all ${
                                        formula.material_ids.includes(mat._id)
                                          ? 'bg-amber-600 text-white border-amber-600'
                                          : 'bg-white text-gray-600 border-gray-300 hover:border-amber-400'
                                      }`}
                                    >
                                      {mat.name}
                                    </button>
                                  ))
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-1">
                                Selected: {formula.material_ids.length} material(s)
                              </p>
                            </div>
                            
                            {/* Formula Expression */}
                            <div>
                              <label className="block text-xs font-medium text-gray-600 mb-1">
                                Formula Expression
                              </label>
                              <textarea
                                value={formula.formula_expression}
                                onChange={(e) => handleUpdateMaterialFormula(index, { ...formula, formula_expression: e.target.value })}
                                className="w-full px-3 py-2 border rounded-lg font-mono text-xs"
                                rows={2}
                                placeholder="e.g., pi * (pow(outer_diameter / 2, 2) - pow((outer_diameter - 2 * thickness) / 2, 2)) * length * density"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
              
              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t">
                <button
                  onClick={handleSaveCalculator}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  {editingCalc._id ? 'Update Calculator' : 'Create Calculator'}
                </button>
                
                <button
                  onClick={() => { setIsEditing(false); setEditingCalc(null); }}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Calculator List */}
        {!isEditing && (
          <div className="bg-white rounded-xl shadow-sm border">
            <div className="p-4 border-b">
              <h2 className="font-semibold">All Calculators ({calculators.length})</h2>
            </div>
            
            {calculators.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Calculator className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>No calculators yet</p>
                <p className="text-sm">Create your first calculator template</p>
              </div>
            ) : (
              <div className="divide-y">
                {calculators.map(calc => {
                  const linkedCategory = categories.find(c => c._id === calc.category_id);
                  
                  return (
                    <div key={calc._id} className="p-4 hover:bg-gray-50">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <h3 className="font-medium">{calc.name}</h3>
                            {calc.is_active === false && (
                              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                                Inactive
                              </span>
                            )}
                          </div>
                          
                          <p className="text-sm text-gray-500 mt-1">
                            {calc.fields.length} fields • Output: {calc.output_label} ({calc.output_unit})
                          </p>
                          
                          <div className="flex items-center gap-3 mt-2 text-xs">
                            {linkedCategory && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                                Category: {linkedCategory.name}
                              </span>
                            )}
                            {calc.material_family && (
                              <span className="px-2 py-1 bg-green-100 text-green-700 rounded">
                                Family: {calc.material_family}
                              </span>
                            )}
                          </div>
                          
                          <div className="mt-2 text-xs text-gray-400 font-mono truncate max-w-lg">
                            {calc.formula_expression}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleEditCalculator(calc)}
                            className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteCalculator(calc._id!)}
                            className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded"
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
        )}
      </div>
    </div>
  );
}
