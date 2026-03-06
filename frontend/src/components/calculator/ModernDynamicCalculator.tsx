'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
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

interface MaterialFormulaOverride {
  material_ids: string[];
  formula_expression: string;
  fields?: CalculatorField[];
  description?: string;
}

interface CalculatorTemplate {
  _id: string;
  name: string;
  slug: string;
  description?: string;
  fields: CalculatorField[];
  formula_expression: string;
  material_formulas?: MaterialFormulaOverride[];
  output_unit: string;
  output_label: string;
  material_family?: string;
  use_material_density: boolean;
}

interface Material {
  _id: string;
  name: string;
  material_family?: string;
  shape_type?: string;
  linked_product_slug?: string;
  calculator_id?: string;
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
  formula_used?: string;
  formula_description?: string;
}

interface ModernDynamicCalculatorProps {
  calculatorId?: string;
  categoryId?: string;
  productName?: string; // For auto-selecting material based on product
  onCalculate?: (result: CalculationResult) => void;
  onMaterialChange?: (material: Material | null) => void; // Callback when material changes
  enableNavigation?: boolean; // Enable navigation to product page when material changes
  showPriceField?: boolean;
  className?: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

// Extract variables used in a formula expression
const extractFormulaVariables = (formula: string): Set<string> => {
  // Remove math functions and operators to get variable names
  const cleaned = formula
    .replace(/\b(pi|pow|sqrt|sin|cos|tan|abs|log|exp|ceil|floor|round|min|max)\b/gi, '')
    .replace(/[\d\.\+\-\*\/\(\)\^\,\s]/g, ' ');
  
  // Extract word tokens (variable names)
  const tokens = cleaned.split(/\s+/).filter(t => t.length > 0 && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(t));
  return new Set(tokens);
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function ModernDynamicCalculator({
  calculatorId,
  categoryId,
  productName,
  onCalculate,
  onMaterialChange,
  enableNavigation = false,
  showPriceField = false,
  className = ''
}: ModernDynamicCalculatorProps) {
  const router = useRouter();
  
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
  
  // Track if initial load is complete (to prevent navigation on first load)
  const [isInitialized, setIsInitialized] = useState(false);

  // Result
  const [result, setResult] = useState<CalculationResult | null>(null);

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
            
            // Auto-select material based on product name if provided
            let autoSelectedMat = null;
            if (productName && mats.length > 0) {
              // Try to find matching material by name (case-insensitive, partial match)
              const productNameLower = productName.toLowerCase();
              autoSelectedMat = mats.find((m: Material) => {
                const matNameLower = m.name.toLowerCase();
                return productNameLower.includes(matNameLower) || matNameLower.includes(productNameLower);
              });
            }
            
            if (autoSelectedMat) {
              setSelectedMaterial(autoSelectedMat._id);
              onMaterialChange?.(autoSelectedMat);
            } else if (mats.length > 0) {
              setSelectedMaterial(mats[0]._id);
              onMaterialChange?.(mats[0]);
            }
          }
        }
        
        // Mark as initialized after first load
        setTimeout(() => setIsInitialized(true), 500);
      } else {
        setError('Calculator not found');
      }
    } catch (err) {
      setError('Failed to load calculator');
    } finally {
      setLoading(false);
    }
  };

  // Get the active formula based on selected material
  const getActiveFormula = useCallback(() => {
    if (!calculator) return { formula: '', fields: [] as CalculatorField[], description: undefined as string | undefined };
    
    // Check if selected material has a specific formula override
    if (selectedMaterial && calculator.material_formulas) {
      for (const override of calculator.material_formulas) {
        if (override.material_ids.includes(selectedMaterial)) {
          // Use override fields if defined, otherwise filter default fields
          const formulaFields = override.fields || calculator.fields;
          return {
            formula: override.formula_expression,
            fields: formulaFields,
            description: override.description
          };
        }
      }
    }
    
    // Default formula
    return {
      formula: calculator.formula_expression,
      fields: calculator.fields,
      description: undefined
    };
  }, [calculator, selectedMaterial]);

  // Get fields that should be displayed based on the active formula
  const getVisibleFields = useCallback(() => {
    const { formula, fields } = getActiveFormula();
    if (!formula || fields.length === 0) return [];
    
    const usedVariables = extractFormulaVariables(formula);
    
    // Always include 'density' and 'material_density' as valid formula variables (not shown as fields)
    usedVariables.delete('density');
    usedVariables.delete('material_density');
    
    // Filter fields to only those used in the formula
    const visibleFields = fields.filter(field => usedVariables.has(field.key));
    
    // Sort by order
    return visibleFields.sort((a, b) => a.order - b.order);
  }, [getActiveFormula]);

  // Perform calculation
  const handleCalculate = useCallback(async () => {
    if (!calculator) return;

    // Get active formula info to determine which fields are needed
    const { formula } = getActiveFormula();
    const usedVariables = extractFormulaVariables(formula);
    usedVariables.delete('density');
    usedVariables.delete('material_density');

    // Check if any required field is missing
    let hasAllRequired = true;
    for (const field of calculator.fields) {
      if (usedVariables.has(field.key) && field.required && !fieldValues[field.key]) {
        hasAllRequired = false;
        break;
      }
    }
    
    if (!hasAllRequired) {
      return;
    }

    // Don't show calculating indicator for quick updates
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
    }
  }, [calculator, fieldValues, fieldUnits, selectedMaterial, quantity, onCalculate, getActiveFormula]);

  // Auto-calculate when values change
  useEffect(() => {
    if (calculator && !loading) {
      const timer = setTimeout(() => {
        handleCalculate();
      }, 500); // Increased debounce time
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      <div className={`w-full rounded-xl border border-gray-200 shadow-lg overflow-hidden ${className}`}>
        <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-white" />
            <span className="text-white font-medium">Loading calculator...</span>
          </div>
        </div>
      </div>
    );
  }

  // Render error state
  if (error || !calculator) {
    return (
      <div className={`w-full rounded-xl border border-gray-200 shadow-lg overflow-hidden ${className}`}>
        <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 px-6 py-4">
          <div className="flex items-center gap-3">
            <Calculator className="h-5 w-5 text-white" />
            <span className="text-white font-medium">Calculator</span>
          </div>
        </div>
        <div className="bg-white p-8 text-center">
          <Calculator className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500">{error || 'No calculator available'}</p>
        </div>
      </div>
    );
  }

  // Get visible fields based on active formula
  const visibleFields = getVisibleFields();
  const { formula: activeFormula, description: formulaDescription } = getActiveFormula();

  return (
    <div className={`w-full rounded-xl border border-gray-200 shadow-lg overflow-hidden ${className}`} data-testid="modern-dynamic-calculator">
      {/* Gradient Header - Keep same colors */}
      <div className="bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 px-6 py-5 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-40 h-40 bg-white rounded-full blur-3xl transform translate-x-20 -translate-y-20"></div>
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-blue-300 rounded-full blur-2xl transform -translate-x-10 translate-y-10"></div>
        </div>
        
        <div className="relative flex items-center justify-between">
          <div className="flex items-center gap-4">
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
          {formulaDescription && (
            <span className="px-3 py-1 bg-white/20 backdrop-blur-sm text-white text-sm font-medium rounded-full">
              {formulaDescription}
            </span>
          )}
        </div>
      </div>

      {/* Calculator Body - White background with dark text */}
      <div className="bg-white p-6 lg:p-8">
        {/* Material Selector */}
        {calculator.use_material_density && materials.length > 0 && (
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Select Material / Product
            </label>
            <div className="relative">
              <select
                value={selectedMaterial}
                onChange={async (e) => {
                  const matId = e.target.value;
                  setSelectedMaterial(matId);
                  const mat = materials.find(m => m._id === matId);
                  onMaterialChange?.(mat || null);
                  
                  // Navigate to product page if enabled
                  if (enableNavigation && isInitialized && mat) {
                    // First try linked_product_slug if it exists
                    if (mat.linked_product_slug) {
                      router.push(`/products/${mat.linked_product_slug}`);
                      return;
                    }
                    
                    // Otherwise, search for product by material name
                    try {
                      const searchRes = await fetch(`${API_URL}/api/products/search?q=${encodeURIComponent(mat.name)}&limit=1`);
                      if (searchRes.ok) {
                        const products = await searchRes.json();
                        if (products.length > 0 && products[0].slug) {
                          router.push(`/products/${products[0].slug}`);
                        }
                      }
                    } catch (err) {
                      console.error('Product search failed:', err);
                    }
                  }
                }}
                className="w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-lg text-gray-900 appearance-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                data-testid="material-selector"
              >
                {materials.map(mat => (
                  <option key={mat._id} value={mat._id}>
                    {mat.name} {mat.density ? `(${mat.density.toLocaleString()} kg/m³)` : ''}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none" />
            </div>
            {selectedMaterialData?.material_family && (
              <p className="text-xs text-gray-500 mt-1.5">
                Material Family: <span className="font-medium text-gray-700">{selectedMaterialData.material_family}</span>
                {enableNavigation && (
                  <span className="ml-2 text-indigo-600">• Select to view product</span>
                )}
              </p>
            )}
          </div>
        )}

        {/* Dynamic Fields - Grid layout - Only show fields used in formula */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
          {visibleFields.map(field => {
            const unitGroup = unitGroups[field.unit_group];
            const units = unitGroup?.units || [];

            return (
              <div key={field.key} className="space-y-2">
                <label className="flex items-center gap-1.5 text-sm font-semibold text-gray-700">
                  {field.label}
                  {field.required && <span className="text-red-500">*</span>}
                </label>
                <div className="flex">
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={fieldValues[field.key] || ''}
                    onChange={(e) => setFieldValues({
                      ...fieldValues,
                      [field.key]: parseFloat(e.target.value) || 0
                    })}
                    className="flex-1 min-w-0 px-4 py-3 bg-gray-50 border border-gray-300 rounded-l-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 transition-all"
                    placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                    data-testid={`field-${field.key}`}
                  />
                  <select
                    value={fieldUnits[field.key] || field.default_unit}
                    onChange={(e) => setFieldUnits({
                      ...fieldUnits,
                      [field.key]: e.target.value
                    })}
                    className="w-20 px-2 py-3 bg-gray-100 border border-l-0 border-gray-300 rounded-r-lg text-gray-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all cursor-pointer"
                    data-testid={`unit-${field.key}`}
                  >
                    {units.map(u => (
                      <option key={u.key} value={u.key}>{u.key}</option>
                    ))}
                  </select>
                </div>
                {field.help_text && (
                  <p className="text-xs text-gray-500">{field.help_text}</p>
                )}
              </div>
            );
          })}

          {/* Quantity */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-700">
              Quantity
            </label>
            <div className="flex">
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="flex-1 min-w-0 px-4 py-3 bg-gray-50 border border-gray-300 rounded-l-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 transition-all"
                data-testid="quantity-field"
              />
              <span className="flex items-center justify-center w-20 px-4 py-3 bg-gray-100 border border-l-0 border-gray-300 rounded-r-lg text-gray-600 text-sm font-medium">
                pcs
              </span>
            </div>
          </div>

          {/* Price Rate (optional) */}
          {showPriceField && (
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-gray-700">
                Rate per {calculator.output_unit}
              </label>
              <div className="flex">
                <span className="flex items-center justify-center w-12 px-3 py-3 bg-gray-100 border border-r-0 border-gray-300 rounded-l-lg text-gray-600 font-medium">
                  ₹
                </span>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={priceRate || ''}
                  onChange={(e) => setPriceRate(parseFloat(e.target.value) || undefined)}
                  className="flex-1 min-w-0 px-4 py-3 bg-gray-50 border border-gray-300 rounded-r-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 transition-all"
                  placeholder="Enter rate"
                  data-testid="price-rate-field"
                />
              </div>
            </div>
          )}
        </div>

        {/* Formula Info - Subtle display */}
        <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-50 px-4 py-2.5 rounded-lg mb-6 border border-gray-100">
          <Info className="h-3.5 w-3.5 flex-shrink-0" />
          <div className="flex flex-col">
            {formulaDescription && (
              <span className="text-gray-600 font-medium">{formulaDescription}</span>
            )}
            <span className="font-mono text-gray-500">{activeFormula}</span>
          </div>
        </div>

        {/* Results - Professional green result card */}
        {result && result.total_value > 0 && (
          <div className="bg-gradient-to-br from-emerald-50 to-green-50 border-2 border-emerald-200 rounded-xl p-6" data-testid="calculation-result">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-emerald-100 rounded-lg">
                  <Sparkles className="h-5 w-5 text-emerald-600" />
                </div>
                <h4 className="font-bold text-lg text-emerald-800">Calculation Result</h4>
              </div>
              {result.formula_description && (
                <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
                  {result.formula_description}
                </span>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl p-5 text-center border border-emerald-100 shadow-sm">
                <p className="text-sm text-emerald-600 font-medium mb-2">{result.output_label} per piece</p>
                <p className="text-3xl font-bold text-gray-900">
                  {result.value_per_piece.toFixed(2)}
                  <span className="text-lg font-medium text-emerald-600 ml-1">{result.output_unit}</span>
                </p>
              </div>
              
              <div className="bg-emerald-600 rounded-xl p-5 text-center shadow-sm">
                <p className="text-sm text-emerald-100 font-medium mb-2">Total ({quantity} pcs)</p>
                <p className="text-3xl font-bold text-white">
                  {formatValue(result.total_value, result.output_unit)}
                </p>
              </div>
            </div>

            {/* Price Estimate */}
            {priceRate && priceRate > 0 && (
              <div className="mt-5 pt-5 border-t-2 border-emerald-200">
                <div className="flex items-center justify-between bg-white rounded-lg p-4 border border-emerald-100">
                  <span className="text-sm text-gray-600">
                    Estimated Price @ <span className="font-semibold text-gray-800">{formatPrice(priceRate)}/{result.output_unit}</span>
                  </span>
                  <span className="text-2xl font-bold text-emerald-700">
                    {formatPrice(result.total_value * priceRate)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
