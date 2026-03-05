'use client';

import { useState, useEffect } from 'react';
import DynamicCalculator from '@/components/calculator/DynamicCalculator';
import { Calculator, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_BACKEND_URL || '';

interface CalculatorTemplate {
  _id: string;
  name: string;
  slug: string;
  description?: string;
}

export default function DynamicCalculatorTestPage() {
  const [calculators, setCalculators] = useState<CalculatorTemplate[]>([]);
  const [selectedCalc, setSelectedCalc] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    loadCalculators();
  }, []);

  const loadCalculators = async () => {
    try {
      const res = await fetch(`${API_URL}/api/calculator/calculators`);
      if (res.ok) {
        const data = await res.json();
        setCalculators(data);
        if (data.length > 0) {
          setSelectedCalc(data[0]._id);
        }
      }
    } catch (err) {
      console.error('Failed to load calculators');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Dynamic Calculator Test
          </h1>
          <p className="text-gray-600">
            Test the configurable calculator system
          </p>
        </div>

        {calculators.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center">
            <Calculator className="h-16 w-16 mx-auto mb-4 text-gray-300" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              No Calculators Available
            </h2>
            <p className="text-gray-600 mb-4">
              Create calculator templates in the admin panel first.
            </p>
            <a
              href="/admin/calculators"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Go to Admin → Calculators
            </a>
          </div>
        ) : (
          <>
            {/* Calculator Selector */}
            <div className="bg-white rounded-xl p-4 mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Calculator
              </label>
              <select
                value={selectedCalc}
                onChange={(e) => {
                  setSelectedCalc(e.target.value);
                  setResult(null);
                }}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-lg"
              >
                {calculators.map(calc => (
                  <option key={calc._id} value={calc._id}>
                    {calc.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Calculator */}
            {selectedCalc && (
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <DynamicCalculator
                    calculatorId={selectedCalc}
                    showPriceField={true}
                    onCalculate={(r) => setResult(r)}
                  />
                </div>

                {/* Result Details */}
                <div className="bg-white rounded-xl p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">
                    Calculation Result
                  </h3>
                  
                  {result ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-sm text-gray-500">Calculator</div>
                          <div className="font-medium">{result.calculator_name}</div>
                        </div>
                        {result.material_name && (
                          <div className="bg-gray-50 p-3 rounded-lg">
                            <div className="text-sm text-gray-500">Material</div>
                            <div className="font-medium">{result.material_name}</div>
                          </div>
                        )}
                        <div className="bg-blue-50 p-3 rounded-lg">
                          <div className="text-sm text-blue-600">{result.output_label}/piece</div>
                          <div className="font-bold text-blue-700">
                            {result.value_per_piece.toFixed(4)} {result.output_unit}
                          </div>
                        </div>
                        <div className="bg-green-50 p-3 rounded-lg">
                          <div className="text-sm text-green-600">Total ({result.quantity} pcs)</div>
                          <div className="font-bold text-green-700">
                            {result.total_value.toFixed(4)} {result.output_unit}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-2">
                          Dimensions Used:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(result.field_summary).map(([key, value]) => (
                            <span
                              key={key}
                              className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                            >
                              {key}: {value as string}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="pt-4 border-t">
                        <div className="text-sm text-gray-500 mb-2">Raw Response:</div>
                        <pre className="bg-gray-900 text-green-400 p-3 rounded-lg text-xs overflow-auto max-h-48">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <Calculator className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                      <p>Enter values to see calculation result</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Admin Links */}
        <div className="mt-8 p-4 bg-white rounded-xl">
          <h3 className="font-semibold mb-3">Admin Panel Links</h3>
          <div className="flex flex-wrap gap-3">
            <a
              href="/admin/calculators"
              className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200"
            >
              Calculator Templates
            </a>
            <a
              href="/admin/unit-groups"
              className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200"
            >
              Unit Groups
            </a>
            <a
              href="/admin/materials"
              className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200"
            >
              Materials
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
