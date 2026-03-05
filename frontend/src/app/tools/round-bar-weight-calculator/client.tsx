'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Round Bar Weight</h2>
    <p className="text-gray-600 mb-6">
      Round bar weight calculation uses the formula for cylinder volume multiplied by material density. 
      The formula is based on the circular cross-section area (π × r²) multiplied by the length.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Round Bar Weight Formula</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Standard Formula</h4>
      <code className="text-blue-700 text-lg">Weight = π × (d/2)² × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">
        Where: d = diameter, L = length, ρ = density (all in SI units)
      </p>
    </div>

    <div className="bg-green-50 rounded-lg p-4 border border-green-200 mb-6">
      <h4 className="font-semibold text-green-800 mb-2">Quick Formula (for MS Steel in mm and meters)</h4>
      <code className="text-green-700 text-lg">Weight (kg) = d² × 0.00617 × L</code>
      <p className="text-sm text-green-600 mt-2">
        Where: d = diameter in mm, L = length in meters
      </p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Types of Round Bars</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">MS Round Bars</h4>
        <p className="text-sm text-gray-600">
          Mild steel bars for general engineering, construction, and fabrication work.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">Bright Bars</h4>
        <p className="text-sm text-gray-600">
          Cold-drawn bars with precise dimensions and smooth finish for machining.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">EN Series Bars</h4>
        <p className="text-sm text-gray-600">
          EN8, EN9, EN19 - high-strength alloy steels for automotive and machinery.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">SS Round Bars</h4>
        <p className="text-sm text-gray-600">
          Stainless steel bars (SS304, SS316) for corrosion-resistant applications.
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Weight Per Meter Reference Table</h3>
    <div className="bg-gray-50 rounded-lg p-4 mb-6 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2 font-semibold">Diameter (mm)</th>
            <th className="text-right py-2 font-semibold">MS Steel (kg/m)</th>
            <th className="text-right py-2 font-semibold">SS304 (kg/m)</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td className="py-2">8</td><td className="text-right">0.395</td><td className="text-right">0.399</td></tr>
          <tr className="border-b"><td className="py-2">10</td><td className="text-right">0.617</td><td className="text-right">0.623</td></tr>
          <tr className="border-b"><td className="py-2">12</td><td className="text-right">0.888</td><td className="text-right">0.897</td></tr>
          <tr className="border-b"><td className="py-2">16</td><td className="text-right">1.578</td><td className="text-right">1.595</td></tr>
          <tr className="border-b"><td className="py-2">20</td><td className="text-right">2.466</td><td className="text-right">2.492</td></tr>
          <tr className="border-b"><td className="py-2">25</td><td className="text-right">3.853</td><td className="text-right">3.893</td></tr>
          <tr className="border-b"><td className="py-2">32</td><td className="text-right">6.313</td><td className="text-right">6.380</td></tr>
          <tr><td className="py-2">50</td><td className="text-right">15.413</td><td className="text-right">15.575</td></tr>
        </tbody>
      </table>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel Round Bar:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Diameter: 20 mm (0.02 m)</li>
        <li>Length: 6 meters</li>
        <li>Density: 7,850 kg/m³</li>
      </ul>
      <p className="mt-3">
        Volume = π × (0.01)² × 6 = 0.001885 m³<br />
        Weight = 0.001885 × 7,850 = <strong>14.8 kg per bar</strong><br />
        <span className="text-sm text-gray-500">Quick check: 20² × 0.00617 × 6 = 14.8 kg ✓</span>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "How do you calculate round bar weight per meter?",
    answer: "Use the formula: Weight/m = π × (d/2)² × 1 × density, or the quick formula for MS steel: Weight (kg/m) = d² × 0.00617, where d is diameter in mm. A 20mm MS round bar weighs 2.47 kg per meter."
  },
  {
    question: "What is the weight of 10mm MS round bar per meter?",
    answer: "A 10mm diameter MS steel round bar weighs approximately 0.617 kg per meter. For a standard 6-meter length, one bar weighs about 3.7 kg."
  },
  {
    question: "What is the difference between round bar and bright bar?",
    answer: "Round bars are hot-rolled with rough surface finish and wider tolerances. Bright bars are cold-drawn with precise dimensions, smooth finish, and tighter tolerances - ideal for machining applications."
  },
  {
    question: "How do I calculate TMT bar weight?",
    answer: "TMT bars use the same formula as round bars since they have a circular cross-section. The nominal diameter is used for calculation. Standard TMT bar weight per meter: 8mm = 0.395 kg, 10mm = 0.617 kg, 12mm = 0.888 kg."
  },
  {
    question: "What is the standard length of round bars in India?",
    answer: "Standard lengths are typically 3 meters, 6 meters, or 12 meters. Some suppliers offer cut-to-length services. TMT bars are commonly available in 12-meter lengths for construction."
  },
  {
    question: "How does EN8 round bar weight compare to MS steel?",
    answer: "EN8 (medium carbon steel) has similar density to MS steel (about 7,850 kg/m³), so the weight per meter is virtually identical. The difference is in mechanical properties - EN8 is harder and stronger."
  }
];

const relatedTools = [
  {
    title: "Steel Weight Calculator",
    href: "/tools/steel-weight-calculator",
    description: "Calculate weight for all steel products including plates and pipes."
  },
  {
    title: "Pipe Weight Calculator",
    href: "/tools/pipe-weight-calculator",
    description: "Calculate hollow pipe and tube weight using OD and wall thickness."
  },
  {
    title: "Plate Weight Calculator",
    href: "/tools/plate-weight-calculator",
    description: "Calculate flat plate and sheet metal weight based on dimensions."
  }
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Round Bar Weight Calculator",
  "description": "Free online calculator to compute round bar and rod weight based on diameter and length. Supports MS Steel, Stainless Steel, EN series, and bright bars.",
  "applicationCategory": "Calculator",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "INR"
  },
  "provider": {
    "@type": "Organization",
    "name": "UdyogConnect",
    "url": "https://udyogconnect.com"
  }
};

export default function RoundBarWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Round Bar Weight Calculator"
      pageDescription="Calculate round bar weight instantly"
      h1Title="Round Bar Weight Calculator"
      h1Subtitle="Calculate weight of MS round bars, bright bars, EN series bars, and TMT bars using diameter and length. Connect with verified bar suppliers."
      defaultMaterial="MS Steel"
      defaultShape="round_bar"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Round Bar Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
