'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Calculator,
  Scale,
  ChevronDown,
  Info,
  RefreshCw,
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
  material_type?: string;
  use_material_density: boolean;
}

interface Material {
  _id: string;
  name: string;
  density?: number;
  weight_per_unit?: Record<string, number>;
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

interface DynamicCalculatorProps {
  calculatorId?: string;
  categoryId?: string;
  onCalculate?: (result: CalculationResult) => void;
  showPriceField?: boolean;
  ratePerKg?: number;
  compact?: boolean;
  className?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function DynamicCalculator({
  calculatorId,
  categoryId,
  onCalculate,
  showPriceField = false,
  ratePerKg,
  compact = false,
  className = ''
}: DynamicCalculatorProps) {
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
  const [priceRate, setPriceRate] = useState<number | undefined>(ratePerKg);

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

        // Load materials if calculator uses them
        if (calcData.use_material_density && calcData.material_type) {
          const matsRes = await fetch(`${API_URL}/api/calculator/materials?material_type=${calcData.material_type}`);
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
        return; // Don't calculate with missing required fields
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

  // Update price rate from prop
  useEffect(() => {
    setPriceRate(ratePerKg);
  }, [ratePerKg]);

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

  // Render loading state
  if (loading) {
    return (
      <div className={`bg-white rounded-xl shadow-sm border p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <span className="ml-3 text-gray-600">Loading calculator...</span>
        </div>
      </div>
    );
  }

  // Render error state
  if (error || !calculator) {
    return (
      <div className={`bg-white rounded-xl shadow-sm border p-6 ${className}`}>
        <div className="text-center py-8 text-gray-500">
          <Calculator className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p>{error || 'No calculator available for this category'}</p>
        </div>
      </div>
    );
  }

  // Sort fields by order
  const sortedFields = [...calculator.fields].sort((a, b) => a.order - b.order);

  return (
    <div className={`bg-white rounded-xl shadow-sm border overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-4 py-3">
        <div className="flex items-center gap-3">
          <Calculator className="h-5 w-5 text-white" />
          <div>
            <h3 className="font-semibold text-white">{calculator.name}</h3>
            {calculator.description && (
              <p className="text-blue-100 text-sm">{calculator.description}</p>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Material Selector */}
        {calculator.use_material_density && materials.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Material
            </label>
            <div className="relative">
              <select
                value={selectedMaterial}
                onChange={(e) => setSelectedMaterial(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg appearance-none bg-white pr-10"
              >
                {materials.map(mat => (
                  <option key={mat._id} value={mat._id}>
                    {mat.name} {mat.density ? `(${mat.density.toLocaleString()} kg/m³)` : ''}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        )}

        {/* Dynamic Fields */}
        <div className={`grid gap-4 ${compact ? 'grid-cols-2' : 'grid-cols-1 sm:grid-cols-2'}`}>
          {sortedFields.map(field => {
            const unitGroup = unitGroups[field.unit_group];
            const units = unitGroup?.units || [];

            return (
              <div key={field.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
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
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                  />
                  <select
                    value={fieldUnits[field.key] || field.default_unit}
                    onChange={(e) => setFieldUnits({
                      ...fieldUnits,
                      [field.key]: e.target.value
                    })}
                    className="w-20 px-2 py-2 border border-gray-300 rounded-lg bg-white"
                  >
                    {units.map(u => (
                      <option key={u.key} value={u.key}>{u.key}</option>
                    ))}
                  </select>
                </div>
                {field.help_text && (
                  <p className="text-xs text-gray-500 mt-1">{field.help_text}</p>
                )}
              </div>
            );
          })}

          {/* Quantity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Quantity
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <span className="flex items-center px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600">
                pcs
              </span>
            </div>
          </div>

          {/* Price Rate (optional) */}
          {showPriceField && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rate per {calculator.output_unit}
              </label>
              <div className="flex gap-2">
                <span className="flex items-center px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-600">
                  ₹
                </span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={priceRate || ''}
                  onChange={(e) => setPriceRate(parseFloat(e.target.value) || undefined)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="Rate"
                />
              </div>
            </div>
          )}
        </div>

        {/* Formula Info */}
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 px-3 py-2 rounded-lg">
          <Info className="h-3 w-3" />
          <span>Formula: {calculator.formula_expression}</span>
        </div>

        {/* Results */}
        {result && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-gray-600">
                  {result.output_label} per piece
                </div>
                <div className="text-xl font-bold text-gray-900">
                  {formatValue(result.value_per_piece, result.output_unit)}
                </div>
              </div>
              
              {quantity > 1 && (
                <div className="text-right">
                  <div className="text-sm text-gray-600">
                    Total {result.output_label} ({quantity} pcs)
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {formatValue(result.total_value, result.output_unit)}
                  </div>
                </div>
              )}
            </div>

            {/* Price Estimate */}
            {priceRate && priceRate > 0 && (
              <div className="mt-3 pt-3 border-t border-green-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    Estimated Price @ {formatPrice(priceRate)}/{result.output_unit}
                  </span>
                  <span className="text-lg font-bold text-green-700">
                    {formatPrice(result.total_value * priceRate)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Calculating indicator */}
        {calculating && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Calculating...
          </div>
        )}
      </div>
    </div>
  );
}
