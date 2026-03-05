'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Calculator,
  ChevronDown,
  Info,
  Loader2,
  Scale,
  Sparkles
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

interface CalculatorTemplate {
  _id: string;
  name: string;
  slug: string;
  description?: string;
  fields: CalculatorField[];
  formula_expression: string;
  output_unit: string;
  output_label: string;
  material_family?: string;
  use_material_density: boolean;
}

interface Material {
  _id: string;
  name: string;
  material_family?: string;
  density?: number;
}

interface CalculationResult {
  calculator_name: string;
  material_name?: string;
  calculated_value: number;
  output_unit: string;
  output_label: string;
  value_per_piece: number;
  total_value: number;
  quantity: number;
  field_summary: Record<string, string>;
}

interface ModernDynamicCalculatorProps {
  calculatorId?: string;
  categoryId?: string;
  onCalculate?: (result: CalculationResult) => void;
  showPriceField?: boolean;
  className?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function ModernDynamicCalculator({
  calculatorId,
  categoryId,
  onCalculate,
  showPriceField = false,
  className = ''
}: ModernDynamicCalculatorProps) {
  // Data states
  const [calculator, setCalculator] = useState<CalculatorTemplate | null>(null);
  const [unitGroups, setUnitGroups] = useState<Record<string, UnitGroup>>({});
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [selectedMaterial, setSelectedMaterial] = useState<string>('');
  const [fieldValues, setFieldValues] = useState<Record<string, number>>({});
  const [fieldUnits, setFieldUnits] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState<number>(1);
  const [priceRate, setPriceRate] = useState<number | undefined>(undefined);

  // Result
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [calculating, setCalculating] = useState(false);

  // Load calculator and data
  useEffect(() => {
    loadData();
  }, [calculatorId, categoryId]);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load unit groups
      const unitsRes = await fetch(`${API_URL}/api/calculator/unit-groups`);
      if (unitsRes.ok) {
        const groups = await unitsRes.json();
        const groupMap: Record<string, UnitGroup> = {};
        groups.forEach((g: UnitGroup) => {
          groupMap[g.name] = g;
        });
        setUnitGroups(groupMap);
      }

      // Load calculator
      let calcData: CalculatorTemplate | null = null;

      if (calculatorId) {
        const calcRes = await fetch(`${API_URL}/api/calculator/calculators/${calculatorId}`);
        if (calcRes.ok) {
          calcData = await calcRes.json();
        }
      } else if (categoryId) {
        const calcRes = await fetch(`${API_URL}/api/calculator/calculators/by-category/${categoryId}`);
        if (calcRes.ok) {
          calcData = await calcRes.json();
        }
      }

      if (calcData) {
        setCalculator(calcData);

        // Initialize field values and units
        const initialValues: Record<string, number> = {};
        const initialUnits: Record<string, string> = {};
        calcData.fields.forEach(field => {
          initialValues[field.key] = 0;
          initialUnits[field.key] = field.default_unit;
        });
        setFieldValues(initialValues);
        setFieldUnits(initialUnits);

        // Load materials - filter by family if specified
        if (calcData.use_material_density) {
          const familyParam = calcData.material_family ? `?family=${calcData.material_family}` : '';
          const matsRes = await fetch(`${API_URL}/api/calculator/materials${familyParam}`);
          if (matsRes.ok) {
            const mats = await matsRes.json();
            setMaterials(mats);
            if (mats.length > 0) {
              setSelectedMaterial(mats[0]._id);
            }
          }
        }
      } else {
        setError('Calculator not found');
      }
    } catch (err) {
      setError('Failed to load calculator');
    } finally {
      setLoading(false);
    }
  };

  // Perform calculation
  const handleCalculate = useCallback(async () => {
    if (!calculator) return;

    // Validate required fields
    for (const field of calculator.fields) {
      if (field.required && !fieldValues[field.key]) {
        return;
      }
    }

    setCalculating(true);

    try {
      const res = await fetch(`${API_URL}/api/calculator/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          calculator_id: calculator._id,
          material_id: selectedMaterial || undefined,
          field_values: fieldValues,
          field_units: fieldUnits,
          quantity
        })
      });

      if (res.ok) {
        const calcResult = await res.json();
        setResult(calcResult);
        onCalculate?.(calcResult);
      }
    } catch (err) {
      console.error('Calculation error:', err);
    } finally {
      setCalculating(false);
    }
  }, [calculator, fieldValues, fieldUnits, selectedMaterial, quantity, onCalculate]);

  // Auto-calculate when values change
  useEffect(() => {
    if (calculator && !loading) {
      const timer = setTimeout(() => {
        handleCalculate();
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [fieldValues, fieldUnits, selectedMaterial, quantity, calculator, loading]);

  // Format helpers
  const formatValue = (value: number, unit: string): string => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)} ${unit === 'kg' ? 'tonnes' : 'k' + unit}`;
    }
    return `${value.toFixed(2)} ${unit}`;
  };

  const formatPrice = (price: number): string => {
    return `₹${price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  // Get selected material info
  const selectedMaterialData = materials.find(m => m._id === selectedMaterial);

  // Render loading state
  if (loading) {
    return (
      <div className={`rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-8 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-blue-400" />
          <span className="ml-3 text-slate-300">Loading calculator...</span>
        </div>
      </div>
    );
  }

  // Render error state
  if (error || !calculator) {
    return (
      <div className={`rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-8 ${className}`}>
        <div className="text-center py-8 text-slate-400">
          <Calculator className="h-12 w-12 mx-auto mb-3 text-slate-600" />
          <p>{error || 'No calculator available'}</p>
        </div>
      </div>
    );
  }

  // Sort fields by order
  const sortedFields = [...calculator.fields].sort((a, b) => a.order - b.order);

  return (
    <div className={`rounded-2xl overflow-hidden shadow-2xl ${className}`}>
      {/* Gradient Header */}
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 px-6 py-5 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-40 h-40 bg-white rounded-full blur-3xl transform translate-x-20 -translate-y-20"></div>
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-blue-300 rounded-full blur-2xl transform -translate-x-10 translate-y-10"></div>
        </div>
        
        <div className="relative flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-sm rounded-xl">
            <Calculator className="h-6 w-6 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-xl text-white">{calculator.name}</h3>
            {calculator.description && (
              <p className="text-white/80 text-sm mt-0.5">{calculator.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Calculator Body */}
      <div className="bg-gradient-to-b from-slate-900 to-slate-950 p-6">
        {/* Material Selector */}
        {calculator.use_material_density && materials.length > 0 && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Select Material
            </label>
            <div className="relative">
              <select
                value={selectedMaterial}
                onChange={(e) => setSelectedMaterial(e.target.value)}
                className="w-full px-4 py-3 bg-slate-800/80 border border-slate-700 rounded-xl text-white appearance-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              >
                {materials.map(mat => (
                  <option key={mat._id} value={mat._id}>
                    {mat.name} {mat.density ? `(${mat.density.toLocaleString()} kg/m³)` : ''}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
            </div>
            {selectedMaterialData?.material_family && (
              <p className="text-xs text-slate-500 mt-1">
                Family: {selectedMaterialData.material_family}
              </p>
            )}
          </div>
        )}

        {/* Dynamic Fields */}
        <div className="grid gap-4 sm:grid-cols-2 mb-6">
          {sortedFields.map(field => {
            const unitGroup = unitGroups[field.unit_group];
            const units = unitGroup?.units || [];

            return (
              <div key={field.key} className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                  {field.label}
                  {field.required && <span className="text-pink-500">*</span>}
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={fieldValues[field.key] || ''}
                    onChange={(e) => setFieldValues({
                      ...fieldValues,
                      [field.key]: parseFloat(e.target.value) || 0
                    })}
                    className="flex-1 px-4 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                  />
                  <select
                    value={fieldUnits[field.key] || field.default_unit}
                    onChange={(e) => setFieldUnits({
                      ...fieldUnits,
                      [field.key]: e.target.value
                    })}
                    className="w-24 px-3 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                  >
                    {units.map(u => (
                      <option key={u.key} value={u.key}>{u.key}</option>
                    ))}
                  </select>
                </div>
                {field.help_text && (
                  <p className="text-xs text-slate-500">{field.help_text}</p>
                )}
              </div>
            );
          })}

          {/* Quantity */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-slate-300">
              Quantity
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="flex-1 px-4 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              />
              <span className="flex items-center px-4 py-3 bg-slate-700/50 border border-slate-700 rounded-xl text-slate-400">
                pcs
              </span>
            </div>
          </div>

          {/* Price Rate (optional) */}
          {showPriceField && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-slate-300">
                Rate per {calculator.output_unit}
              </label>
              <div className="flex gap-2">
                <span className="flex items-center px-4 py-3 bg-slate-700/50 border border-slate-700 rounded-xl text-slate-400">
                  ₹
                </span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={priceRate || ''}
                  onChange={(e) => setPriceRate(parseFloat(e.target.value) || undefined)}
                  className="flex-1 px-4 py-3 bg-slate-800/60 border border-slate-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                  placeholder="Rate"
                />
              </div>
            </div>
          )}
        </div>

        {/* Formula Info */}
        <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-800/30 px-4 py-2 rounded-lg mb-6">
          <Info className="h-3 w-3" />
          <span className="font-mono">{calculator.formula_expression}</span>
        </div>

        {/* Results */}
        {result && result.total_value > 0 && (
          <div className="relative">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/20 via-green-500/20 to-teal-500/20 blur-xl rounded-2xl"></div>
            
            <div className="relative bg-gradient-to-br from-emerald-900/40 to-green-900/40 border border-emerald-500/30 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-emerald-400" />
                <h4 className="font-semibold text-emerald-300">Calculation Result</h4>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-black/20 rounded-xl p-4 text-center">
                  <p className="text-sm text-emerald-400/80 mb-1">{result.output_label} per piece</p>
                  <p className="text-2xl font-bold text-white">
                    {result.value_per_piece.toFixed(2)}
                    <span className="text-lg font-normal text-emerald-300 ml-1">{result.output_unit}</span>
                  </p>
                </div>
                
                <div className="bg-emerald-500/20 rounded-xl p-4 text-center border border-emerald-500/30">
                  <p className="text-sm text-emerald-400/80 mb-1">Total ({quantity} pcs)</p>
                  <p className="text-2xl font-bold text-emerald-300">
                    {formatValue(result.total_value, result.output_unit)}
                  </p>
                </div>
              </div>

              {/* Price Estimate */}
              {priceRate && priceRate > 0 && (
                <div className="mt-4 pt-4 border-t border-emerald-500/20">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-emerald-400/80">
                      Estimated Price @ {formatPrice(priceRate)}/{result.output_unit}
                    </span>
                    <span className="text-xl font-bold text-emerald-300">
                      {formatPrice(result.total_value * priceRate)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Calculating indicator */}
        {calculating && (
          <div className="flex items-center gap-2 text-sm text-indigo-400 mt-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            Calculating...
          </div>
        )}
      </div>
    </div>
  );
}
