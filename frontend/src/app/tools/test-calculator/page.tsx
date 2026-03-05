'use client';

import { useState } from 'react';
import { Calculator, ArrowLeft, Package, Scale, DollarSign } from 'lucide-react';
import Link from 'next/link';
import MaterialCalculatorCard, { CalculationResult } from '@/components/calculator/MaterialCalculatorCard';
import SellerPriceComparison, { RawMaterialSeller } from '@/components/calculator/SellerPriceComparison';

/**
 * Test Calculator Page
 * Route: /tools/test-calculator
 * 
 * Purpose: Test and validate the weight calculator component
 * before integrating into product pages.
 */
export default function TestCalculatorPage() {
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [showPriceComparison, setShowPriceComparison] = useState(false);
  
  // Mock product ID for testing seller price comparison
  // In production, this would come from the actual product page
  const mockProductId = '';

  const handleCalculation = (result: CalculationResult) => {
    setCalculationResult(result);
    console.log('Calculation result:', result);
  };

  const handleInquiry = (seller: RawMaterialSeller, calculatedPrice: number) => {
    console.log('Inquiry for seller:', seller.sellerName);
    console.log('Calculated price:', calculatedPrice);
    alert(`Inquiry sent to ${seller.sellerName} for ₹${calculatedPrice.toLocaleString('en-IN')}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link 
                href="/" 
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
              >
                <ArrowLeft className="h-4 w-4" />
                <span className="text-sm">Home</span>
              </Link>
              <div className="h-6 w-px bg-gray-200" />
              <div className="flex items-center gap-2">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Calculator className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h1 className="font-semibold text-gray-900">Weight Calculator Test</h1>
                  <p className="text-xs text-gray-500">Testing raw material calculator</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Link
                href="/admin/materials"
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Manage Materials
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Page Title */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Raw Material Weight Calculator
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Calculate the weight of steel, stainless steel, aluminum, and other materials 
            based on shape and dimensions. Get instant results with real-time calculations.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Calculator */}
          <div className="lg:col-span-2">
            <MaterialCalculatorCard
              onCalculate={handleCalculation}
              defaultMaterial="MS Steel"
              defaultShape="round_bar"
              showPriceField={true}
              className="shadow-lg"
            />

            {/* Calculation History / Debug Info */}
            {calculationResult && (
              <div className="mt-6 bg-white rounded-xl shadow-sm border p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <Scale className="h-5 w-5 text-gray-500" />
                  Calculation Details
                </h3>
                <div className="grid md:grid-cols-2 gap-4 text-sm">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Shape:</span>
                      <span className="font-medium capitalize">{calculationResult.shape.replace('_', ' ')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Material:</span>
                      <span className="font-medium">{calculationResult.material}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Density:</span>
                      <span className="font-medium">{calculationResult.density.toLocaleString()} kg/m³</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Quantity:</span>
                      <span className="font-medium">{calculationResult.quantity} pieces</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Volume/piece:</span>
                      <span className="font-mono text-xs">{calculationResult.volume_per_piece.toFixed(8)} m³</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Weight/piece:</span>
                      <span className="font-medium">{calculationResult.weight_per_piece_display}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total Weight:</span>
                      <span className="font-bold text-blue-600">{calculationResult.total_weight_display}</span>
                    </div>
                    {calculationResult.total_price_display && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Total Price:</span>
                        <span className="font-bold text-green-600">{calculationResult.total_price_display}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Dimensions */}
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm text-gray-500 mb-2">Dimensions:</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(calculationResult.dimensions).map(([key, value]) => (
                      <span 
                        key={key} 
                        className="px-3 py-1 bg-gray-100 rounded-full text-sm"
                      >
                        {key.replace('_', ' ')}: {value}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Info */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Package className="h-5 w-5 text-gray-500" />
                Supported Shapes
              </h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  Round Bar - Solid circular bar
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  Square Bar - Solid square bar
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  Pipe / Tube - Hollow circular
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  Plate - Flat rectangular stock
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                  Sheet - Thin flat stock
                </li>
              </ul>
            </div>

            {/* Unit Info */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-gray-500" />
                Supported Units
              </h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-medium text-gray-700">Length</p>
                  <p className="text-gray-500">mm, cm, meter, inch, feet</p>
                </div>
                <div>
                  <p className="font-medium text-gray-700">Diameter / Side</p>
                  <p className="text-gray-500">mm, cm, inch</p>
                </div>
                <div>
                  <p className="font-medium text-gray-700">Thickness</p>
                  <p className="text-gray-500">mm, cm, inch</p>
                </div>
              </div>
            </div>

            {/* Testing Notes */}
            <div className="bg-amber-50 rounded-xl border border-amber-200 p-6">
              <h3 className="font-semibold text-amber-800 mb-2">Testing Notes</h3>
              <ul className="text-sm text-amber-700 space-y-1">
                <li>• All calculations happen client-side</li>
                <li>• Materials loaded from database</li>
                <li>• Results update in real-time</li>
                <li>• Formula displayed for verification</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Seller Price Comparison Section */}
        {calculationResult && calculationResult.total_weight > 0 && mockProductId && (
          <div className="mt-8">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-gray-900">
                  Compare Seller Prices
                </h3>
                <button
                  onClick={() => setShowPriceComparison(!showPriceComparison)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  {showPriceComparison ? 'Hide' : 'Show'} Comparison
                </button>
              </div>

              {showPriceComparison && (
                <SellerPriceComparison
                  productId={mockProductId}
                  material={calculationResult.material}
                  totalWeight={calculationResult.total_weight}
                  onInquiry={handleInquiry}
                />
              )}
            </div>
          </div>
        )}

        {/* API Test Section */}
        <div className="mt-8 bg-white rounded-xl shadow-sm border p-6">
          <h3 className="font-semibold text-gray-900 mb-4">API Endpoints</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-mono text-xs text-gray-500">GET</p>
              <p className="font-mono text-blue-600">/api/raw-materials/materials</p>
              <p className="text-gray-500 mt-1">Get all materials with densities</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-mono text-xs text-gray-500">GET</p>
              <p className="font-mono text-blue-600">/api/raw-materials/shapes</p>
              <p className="text-gray-500 mt-1">Get all shape configurations</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-mono text-xs text-gray-500">POST</p>
              <p className="font-mono text-blue-600">/api/raw-materials/calculate</p>
              <p className="text-gray-500 mt-1">Server-side weight calculation</p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="font-mono text-xs text-gray-500">GET</p>
              <p className="font-mono text-blue-600">/api/raw-materials/sellers/raw-material/:productId</p>
              <p className="text-gray-500 mt-1">Get sellers with rate/kg pricing</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 border-t bg-white py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>Raw Material Calculator - Test Page</p>
          <p className="mt-1">All calculations are for estimation purposes only.</p>
        </div>
      </footer>
    </div>
  );
}
