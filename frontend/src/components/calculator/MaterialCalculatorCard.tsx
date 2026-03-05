'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Calculator,
  Scale,
  Package,
  ChevronDown,
  Info,
  RefreshCw,
  Loader2
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

// ============================================================================
// TYPES
// ============================================================================

export interface Material {
  _id?: string;
  name: string;
  density: number;
  description?: string;
}

export interface ShapeField {
  key: string;
  label: string;
  unit_options: string[];
  default_unit: string;
  required: boolean;
}

export interface ShapeConfig {
  key: string;
  name: string;
  description: string;
  fields: ShapeField[];
  formula: string;
  icon: string;
}

export interface CalculationResult {
  shape: string;
  material: string;
  density: number;
  volume_per_piece: number;
  weight_per_piece: number;
  total_weight: number;
  rate_per_kg?: number;
  total_price?: number;
  dimensions: Record<string, string>;
  quantity: number;
  weight_per_piece_display: string;
  total_weight_display: string;
  total_price_display?: string;
}

export interface MaterialCalculatorProps {
  onCalculate?: (result: CalculationResult) => void;
  defaultMaterial?: string;
  defaultShape?: string;
  showPriceField?: boolean;
  ratePerKg?: number;
  compact?: boolean;
  className?: string;
}

// ============================================================================
// UNIT CONVERSION (Client-side)
// ============================================================================

const UNIT_TO_METERS: Record<string, number> = {
  mm: 0.001,
  cm: 0.01,
  meter: 1.0,
  m: 1.0,
  inch: 0.0254,
  in: 0.0254,
  feet: 0.3048,
  ft: 0.3048,
};

function convertToMeters(value: number, unit: string): number {
  const factor = UNIT_TO_METERS[unit.toLowerCase()] || 1.0;
  return value * factor;
}

function formatWeight(weightKg: number): string {
  if (weightKg >= 1000) {
    return `${(weightKg / 1000).toFixed(2)} tonnes`;
  } else if (weightKg >= 1) {
    return `${weightKg.toFixed(2)} kg`;
  } else {
    return `${(weightKg * 1000).toFixed(2)} g`;
  }
}

function formatPrice(price: number): string {
  if (price >= 100000) {
    return `₹${(price / 100000).toFixed(2)} L`;
  } else if (price >= 1000) {
    return `₹${price.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  } else {
    return `₹${price.toFixed(2)}`;
  }
}

// ============================================================================
// CLIENT-SIDE CALCULATION ENGINE
// ============================================================================

function calculateVolume(
  shape: string,
  dimensions: Record<string, number>,
  units: Record<string, string>
): number {
  const getMeters = (key: string) => convertToMeters(dimensions[key] || 0, units[key] || 'mm');

  switch (shape.toLowerCase()) {
    case 'round_bar': {
      const diameter = getMeters('diameter');
      const length = getMeters('length');
      return Math.PI * Math.pow(diameter / 2, 2) * length;
    }
    case 'square_bar': {
      const side = getMeters('side');
      const length = getMeters('length');
      return Math.pow(side, 2) * length;
    }
    case 'pipe': {
      const od = getMeters('outer_diameter');
      const thickness = getMeters('thickness');
      const length = getMeters('length');
      const id = od - 2 * thickness;
      if (id <= 0) return 0;
      return Math.PI * (Math.pow(od / 2, 2) - Math.pow(id / 2, 2)) * length;
    }
    case 'plate':
    case 'sheet': {
      const thickness = getMeters('thickness');
      const width = getMeters('width');
      const length = getMeters('length');
      return thickness * width * length;
    }
    default:
      return 0;
  }
}

function calculateWeight(
  shape: string,
  material: Material,
  dimensions: Record<string, number>,
  units: Record<string, string>,
  quantity: number,
  ratePerKg?: number
): CalculationResult | null {
  if (!material || !shape) return null;

  const volume = calculateVolume(shape, dimensions, units);
  if (volume <= 0) return null;

  const weightPerPiece = volume * material.density;
  const totalWeight = weightPerPiece * quantity;
  const totalPrice = ratePerKg ? totalWeight * ratePerKg : undefined;

  // Build dimensions display
  const dimensionsDisplay: Record<string, string> = {};
  Object.keys(dimensions).forEach(key => {
    if (dimensions[key]) {
      dimensionsDisplay[key] = `${dimensions[key]} ${units[key] || 'mm'}`;
    }
  });

  return {
    shape,
    material: material.name,
    density: material.density,
    volume_per_piece: volume,
    weight_per_piece: weightPerPiece,
    total_weight: totalWeight,
    rate_per_kg: ratePerKg,
    total_price: totalPrice,
    dimensions: dimensionsDisplay,
    quantity,
    weight_per_piece_display: formatWeight(weightPerPiece),
    total_weight_display: formatWeight(totalWeight),
    total_price_display: totalPrice ? formatPrice(totalPrice) : undefined,
  };
}

// ============================================================================
// DEFAULT DATA
// ============================================================================

const DEFAULT_MATERIALS: Material[] = [
  { name: 'MS Steel', density: 7850, description: 'Mild Steel / Carbon Steel' },
  { name: 'SS304', density: 7930, description: 'Stainless Steel 304' },
  { name: 'SS316', density: 8000, description: 'Stainless Steel 316' },
  { name: 'Aluminum', density: 2700, description: 'Aluminum Alloy' },
  { name: 'Copper', density: 8960, description: 'Pure Copper' },
  { name: 'Brass', density: 8500, description: 'Brass Alloy' },
];

const DEFAULT_SHAPES: ShapeConfig[] = [
  {
    key: 'round_bar',
    name: 'Round Bar',
    description: 'Solid circular cross-section bar',
    fields: [
      { key: 'diameter', label: 'Diameter', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
      { key: 'length', label: 'Length', unit_options: ['meter', 'feet', 'cm'], default_unit: 'meter', required: true },
    ],
    formula: 'V = π × (d/2)² × L',
    icon: 'circle',
  },
  {
    key: 'square_bar',
    name: 'Square Bar',
    description: 'Solid square cross-section bar',
    fields: [
      { key: 'side', label: 'Side', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
      { key: 'length', label: 'Length', unit_options: ['meter', 'feet', 'cm'], default_unit: 'meter', required: true },
    ],
    formula: 'V = side² × L',
    icon: 'square',
  },
  {
    key: 'pipe',
    name: 'Pipe / Tube',
    description: 'Hollow circular cross-section',
    fields: [
      { key: 'outer_diameter', label: 'Outer Diameter (OD)', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
      { key: 'thickness', label: 'Wall Thickness', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
      { key: 'length', label: 'Length', unit_options: ['meter', 'feet', 'cm'], default_unit: 'meter', required: true },
    ],
    formula: 'V = π × ((OD/2)² - ((OD-2t)/2)²) × L',
    icon: 'circle-dot',
  },
  {
    key: 'plate',
    name: 'Plate',
    description: 'Flat rectangular stock',
    fields: [
      { key: 'thickness', label: 'Thickness', unit_options: ['mm', 'cm', 'inch'], default_unit: 'mm', required: true },
      { key: 'width', label: 'Width', unit_options: ['mm', 'cm', 'meter', 'feet'], default_unit: 'mm', required: true },
      { key: 'length', label: 'Length', unit_options: ['meter', 'feet', 'cm'], default_unit: 'meter', required: true },
    ],
    formula: 'V = thickness × width × length',
    icon: 'rectangle-horizontal',
  },
  {
    key: 'sheet',
    name: 'Sheet',
    description: 'Thin flat stock',
    fields: [
      { key: 'thickness', label: 'Thickness', unit_options: ['mm', 'cm'], default_unit: 'mm', required: true },
      { key: 'width', label: 'Width', unit_options: ['mm', 'cm', 'meter', 'feet'], default_unit: 'mm', required: true },
      { key: 'length', label: 'Length', unit_options: ['meter', 'feet', 'cm'], default_unit: 'meter', required: true },
    ],
    formula: 'V = thickness × width × length',
    icon: 'layers',
  },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function MaterialCalculatorCard({
  onCalculate,
  defaultMaterial = 'MS Steel',
  defaultShape = 'round_bar',
  showPriceField = false,
  ratePerKg: externalRate,
  compact = false,
  className = '',
}: MaterialCalculatorProps) {
  // Ref to store onCalculate callback (prevents infinite re-render)
  const onCalculateRef = useRef(onCalculate);
  useEffect(() => {
    onCalculateRef.current = onCalculate;
  }, [onCalculate]);

  // Data states
  const [materials, setMaterials] = useState<Material[]>(DEFAULT_MATERIALS);
  const [shapes] = useState<ShapeConfig[]>(DEFAULT_SHAPES);
  const [loadingMaterials, setLoadingMaterials] = useState(true);

  // Form states
  const [selectedMaterial, setSelectedMaterial] = useState<string>(defaultMaterial);
  const [selectedShape, setSelectedShape] = useState<string>(defaultShape);
  const [dimensions, setDimensions] = useState<Record<string, number>>({});
  const [units, setUnits] = useState<Record<string, string>>({});
  const [quantity, setQuantity] = useState<number>(1);
  const [ratePerKg, setRatePerKg] = useState<number | undefined>(externalRate);

  // Result
  const [result, setResult] = useState<CalculationResult | null>(null);

  // Load materials from API
  useEffect(() => {
    const loadMaterials = async () => {
      try {
        const res = await fetch(`${API_URL}/api/raw-materials/materials`);
        if (res.ok) {
          const data = await res.json();
          if (data.length > 0) {
            setMaterials(data);
          }
        }
      } catch (err) {
        console.log('Using default materials');
      } finally {
        setLoadingMaterials(false);
      }
    };
    loadMaterials();
  }, []);

  // Get current shape config
  const currentShape = useMemo(() => {
    return shapes.find(s => s.key === selectedShape) || shapes[0];
  }, [shapes, selectedShape]);

  // Get current material
  const currentMaterial = useMemo(() => {
    return materials.find(m => m.name === selectedMaterial) || materials[0];
  }, [materials, selectedMaterial]);

  // Initialize units when shape changes
  useEffect(() => {
    if (currentShape) {
      const newUnits: Record<string, string> = {};
      currentShape.fields.forEach(field => {
        newUnits[field.key] = field.default_unit;
      });
      setUnits(newUnits);
      setDimensions({});
      setResult(null);
    }
  }, [currentShape]);

  // Update external rate
  useEffect(() => {
    if (externalRate !== undefined) {
      setRatePerKg(externalRate);
    }
  }, [externalRate]);

  // Calculate weight (client-side, real-time)
  const handleCalculate = useCallback(() => {
    if (!currentMaterial || !currentShape) return;

    // Check required fields
    const hasRequiredFields = currentShape.fields.every(
      field => !field.required || (dimensions[field.key] && dimensions[field.key] > 0)
    );

    if (!hasRequiredFields) {
      setResult(null);
      return;
    }

    const calculationResult = calculateWeight(
      selectedShape,
      currentMaterial,
      dimensions,
      units,
      quantity,
      ratePerKg
    );

    setResult(calculationResult);
    
    if (calculationResult && onCalculateRef.current) {
      onCalculateRef.current(calculationResult);
    }
  }, [currentMaterial, currentShape, selectedShape, dimensions, units, quantity, ratePerKg]);

  // Auto-calculate when inputs change
  useEffect(() => {
    handleCalculate();
  }, [handleCalculate]);

  // Handle dimension change
  const handleDimensionChange = (key: string, value: string) => {
    const numValue = parseFloat(value) || 0;
    setDimensions(prev => ({ ...prev, [key]: numValue }));
  };

  // Handle unit change
  const handleUnitChange = (key: string, unit: string) => {
    setUnits(prev => ({ ...prev, [key]: unit }));
  };

  // Reset form
  const handleReset = () => {
    setDimensions({});
    setQuantity(1);
    setRatePerKg(externalRate);
    setResult(null);
  };

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white">
        <div className="flex items-center gap-3">
          <Calculator className="h-6 w-6" />
          <div>
            <h3 className="font-semibold text-lg">Weight Calculator</h3>
            <p className="text-blue-100 text-sm">Calculate material weight instantly</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Material & Shape Selection */}
        <div className={compact ? 'grid grid-cols-2 gap-4' : 'grid md:grid-cols-2 gap-4'}>
          {/* Material Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Material
            </label>
            <div className="relative">
              <select
                value={selectedMaterial}
                onChange={(e) => setSelectedMaterial(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg appearance-none bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="material-select"
              >
                {materials.map((mat) => (
                  <option key={mat.name} value={mat.name}>
                    {mat.name} ({mat.density.toLocaleString()} kg/m³)
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Shape Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Shape
            </label>
            <div className="relative">
              <select
                value={selectedShape}
                onChange={(e) => setSelectedShape(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg appearance-none bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="shape-select"
              >
                {shapes.map((shape) => (
                  <option key={shape.key} value={shape.key}>
                    {shape.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Dimension Inputs */}
        <div className={compact ? 'grid grid-cols-2 gap-4' : 'grid md:grid-cols-3 gap-4'}>
          {currentShape?.fields.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                {field.label} {field.required && <span className="text-red-500">*</span>}
              </label>
              <div className="flex">
                <input
                  type="number"
                  value={dimensions[field.key] || ''}
                  onChange={(e) => handleDimensionChange(field.key, e.target.value)}
                  placeholder="0"
                  min="0"
                  step="any"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-l-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid={`dimension-${field.key}`}
                />
                <select
                  value={units[field.key] || field.default_unit}
                  onChange={(e) => handleUnitChange(field.key, e.target.value)}
                  className="px-2 py-2 border border-l-0 border-gray-300 rounded-r-lg bg-gray-50 text-sm"
                  data-testid={`unit-${field.key}`}
                >
                  {field.unit_options.map((unit) => (
                    <option key={unit} value={unit}>{unit}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}

          {/* Quantity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Quantity
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              min="1"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              data-testid="quantity-input"
            />
          </div>

          {/* Rate per kg (optional) */}
          {showPriceField && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Rate (₹/kg)
              </label>
              <input
                type="number"
                value={ratePerKg || ''}
                onChange={(e) => setRatePerKg(parseFloat(e.target.value) || undefined)}
                placeholder="e.g., 70"
                min="0"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="rate-input"
              />
            </div>
          )}
        </div>

        {/* Formula Info */}
        {currentShape && (
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-600">
            <Info className="h-4 w-4 text-gray-400" />
            <span>Formula: <code className="bg-gray-200 px-1.5 py-0.5 rounded text-xs">{currentShape.formula}</code></span>
          </div>
        )}

        {/* Results Section */}
        {result && (
          <div className="mt-4 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-green-800 flex items-center gap-2">
                <Scale className="h-5 w-5" />
                Calculation Result
              </h4>
              <button
                onClick={handleReset}
                className="text-sm text-green-600 hover:text-green-800 flex items-center gap-1"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Reset
              </button>
            </div>
            
            <div className={compact ? 'grid grid-cols-2 gap-4' : 'grid md:grid-cols-3 gap-4'}>
              <div className="bg-white p-3 rounded-lg shadow-sm">
                <p className="text-xs text-gray-500 uppercase mb-1">Weight per Piece</p>
                <p className="text-lg font-bold text-gray-900">{result.weight_per_piece_display}</p>
              </div>
              
              <div className="bg-white p-3 rounded-lg shadow-sm">
                <p className="text-xs text-gray-500 uppercase mb-1">Total Weight ({quantity} pcs)</p>
                <p className="text-lg font-bold text-gray-900">{result.total_weight_display}</p>
              </div>
              
              {result.total_price_display && (
                <div className="bg-white p-3 rounded-lg shadow-sm">
                  <p className="text-xs text-gray-500 uppercase mb-1">Estimated Price</p>
                  <p className="text-lg font-bold text-green-600">{result.total_price_display}</p>
                </div>
              )}
            </div>

            {/* Dimension Summary */}
            <div className="mt-3 pt-3 border-t border-green-200 text-sm text-green-800">
              <span className="font-medium">{result.material}</span> • 
              <span className="capitalize ml-1">{result.shape.replace('_', ' ')}</span> • 
              {Object.entries(result.dimensions).map(([key, value]) => (
                <span key={key} className="ml-2">
                  {key.replace('_', ' ')}: {value}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export { calculateWeight, formatWeight, formatPrice, DEFAULT_MATERIALS, DEFAULT_SHAPES };
export type { CalculationResult as WeightCalculationResult };
