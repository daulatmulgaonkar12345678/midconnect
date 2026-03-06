'use client';

import { useState, useEffect } from 'react';
import ModernDynamicCalculator from '@/components/calculator/ModernDynamicCalculator';
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
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 py-12">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-white mb-3">
            Material Weight Calculator
          </h1>
          <p className="text-slate-400">
            Calculate weight of raw materials with precision
          </p>
        </div>

        {calculators.length === 0 ? (
          <div className="bg-slate-800/50 backdrop-blur rounded-2xl p-8 text-center border border-slate-700">
            <Calculator className="h-16 w-16 mx-auto mb-4 text-slate-600" />
            <h2 className="text-xl font-semibold text-white mb-2">
              No Calculators Available
            </h2>
            <p className="text-slate-400 mb-4">
              Create calculator templates in the admin panel first.
            </p>
            <a
              href="/admin/calculators"
              className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Go to Admin → Calculators
            </a>
          </div>
        ) : (
          <>
            {/* Calculator Selector */}
            <div className="bg-slate-800/30 backdrop-blur rounded-2xl p-4 mb-6 border border-slate-700/50">
              <label className="block text-sm font-medium text-slate-400 mb-2">
                Select Calculator Type
              </label>
              <select
                value={selectedCalc}
                onChange={(e) => {
                  setSelectedCalc(e.target.value);
                  setResult(null);
                }}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
              <div className="grid lg:grid-cols-2 gap-6">
                <div>
                  <ModernDynamicCalculator
                    calculatorId={selectedCalc}
                    showPriceField={true}
                    enableNavigation={true}
                    onCalculate={(r) => setResult(r)}
                  />
                </div>

                {/* Result Details */}
                <div className="bg-slate-800/30 backdrop-blur rounded-2xl p-6 border border-slate-700/50">
                  <h3 className="font-semibold text-white mb-4 text-lg">
                    Calculation Details
                  </h3>
                  
                  {result ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/30">
                          <div className="text-sm text-slate-500">Calculator</div>
                          <div className="font-medium text-white">{result.calculator_name}</div>
                        </div>
                        {result.material_name && (
                          <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/30">
                            <div className="text-sm text-slate-500">Material</div>
                            <div className="font-medium text-white">{result.material_name}</div>
                          </div>
                        )}
                        <div className="bg-indigo-900/30 p-4 rounded-xl border border-indigo-500/30">
                          <div className="text-sm text-indigo-400">{result.output_label}/piece</div>
                          <div className="font-bold text-indigo-300 text-xl">
                            {result.value_per_piece.toFixed(4)} {result.output_unit}
                          </div>
                        </div>
                        <div className="bg-emerald-900/30 p-4 rounded-xl border border-emerald-500/30">
                          <div className="text-sm text-emerald-400">Total ({result.quantity} pcs)</div>
                          <div className="font-bold text-emerald-300 text-xl">
                            {result.total_value.toFixed(4)} {result.output_unit}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="text-sm font-medium text-slate-400 mb-2">
                          Dimensions Used:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {Object.entries(result.field_summary).map(([key, value]) => (
                            <span
                              key={key}
                              className="px-3 py-1 bg-slate-900/50 text-slate-300 text-sm rounded-full border border-slate-700/30"
                            >
                              {key}: {value as string}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="pt-4 border-t border-slate-700/50">
                        <div className="text-sm text-slate-500 mb-2">Raw Response:</div>
                        <pre className="bg-slate-950 text-emerald-400 p-4 rounded-xl text-xs overflow-auto max-h-48 border border-slate-800">
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-slate-500">
                      <Calculator className="h-12 w-12 mx-auto mb-3 text-slate-700" />
                      <p>Enter values to see calculation result</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Admin Links */}
        <div className="mt-10 p-4 bg-slate-800/20 rounded-2xl border border-slate-700/30">
          <h3 className="font-semibold text-white mb-3">Admin Panel Links</h3>
          <div className="flex flex-wrap gap-3">
            <a
              href="/admin/calculators"
              className="px-4 py-2 bg-indigo-500/20 text-indigo-400 rounded-lg hover:bg-indigo-500/30 border border-indigo-500/30 transition-colors"
            >
              Calculator Templates
            </a>
            <a
              href="/admin/unit-groups"
              className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 border border-purple-500/30 transition-colors"
            >
              Unit Groups
            </a>
            <a
              href="/admin/materials"
              className="px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg hover:bg-emerald-500/30 border border-emerald-500/30 transition-colors"
            >
              Materials
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
