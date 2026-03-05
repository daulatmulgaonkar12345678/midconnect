'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Steel Weight</h2>
    <p className="text-gray-600 mb-6">
      Steel weight calculation depends on the shape of the material and its density. 
      The basic formula is: <strong>Weight = Volume × Density</strong>. 
      Different steel grades have different densities, which affects the final weight.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Steel Density Values</h3>
    <div className="bg-gray-50 rounded-lg p-4 mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2 font-semibold">Material</th>
            <th className="text-right py-2 font-semibold">Density (kg/m³)</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td className="py-2">MS Steel (Mild Steel)</td><td className="text-right">7,850</td></tr>
          <tr className="border-b"><td className="py-2">SS304 (Stainless Steel)</td><td className="text-right">7,930</td></tr>
          <tr className="border-b"><td className="py-2">SS316 (Stainless Steel)</td><td className="text-right">8,000</td></tr>
          <tr className="border-b"><td className="py-2">Aluminum</td><td className="text-right">2,700</td></tr>
          <tr><td className="py-2">Copper</td><td className="text-right">8,960</td></tr>
        </tbody>
      </table>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Weight Calculation Formulas</h3>
    
    <div className="space-y-4 mb-6">
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="font-semibold text-blue-800 mb-2">Round Bar Weight Formula</h4>
        <code className="text-blue-700">Weight = π × (d/2)² × L × ρ</code>
        <p className="text-sm text-blue-600 mt-2">Where d = diameter, L = length, ρ = density</p>
      </div>

      <div className="bg-green-50 rounded-lg p-4 border border-green-200">
        <h4 className="font-semibold text-green-800 mb-2">Square Bar Weight Formula</h4>
        <code className="text-green-700">Weight = side² × L × ρ</code>
        <p className="text-sm text-green-600 mt-2">Where side = cross-section side, L = length, ρ = density</p>
      </div>

      <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
        <h4 className="font-semibold text-purple-800 mb-2">Pipe Weight Formula</h4>
        <code className="text-purple-700">Weight = π × ((OD/2)² - (ID/2)²) × L × ρ</code>
        <p className="text-sm text-purple-600 mt-2">Where OD = outer diameter, ID = inner diameter, L = length, ρ = density</p>
      </div>

      <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
        <h4 className="font-semibold text-orange-800 mb-2">Plate/Sheet Weight Formula</h4>
        <code className="text-orange-700">Weight = thickness × width × length × ρ</code>
        <p className="text-sm text-orange-600 mt-2">All dimensions in meters, ρ = density in kg/m³</p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel Round Bar:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Diameter: 20 mm (0.02 m)</li>
        <li>Length: 6 meters</li>
        <li>Density: 7,850 kg/m³</li>
      </ul>
      <p className="mt-3 font-medium">
        Volume = π × (0.01)² × 6 = 0.001885 m³<br />
        Weight = 0.001885 × 7,850 = <strong>14.8 kg per piece</strong>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "What is the density of MS steel?",
    answer: "Mild Steel (MS) has a density of approximately 7,850 kg/m³ or 7.85 g/cm³. This is the standard value used in weight calculations for MS steel products like round bars, plates, and pipes."
  },
  {
    question: "How do you calculate round bar weight?",
    answer: "Round bar weight is calculated using the formula: Weight = π × (diameter/2)² × length × density. For MS steel with diameter 20mm and length 6m: Weight = 3.14159 × (0.01)² × 6 × 7850 = 14.8 kg"
  },
  {
    question: "What is the difference between SS304 and SS316 density?",
    answer: "SS304 has a density of 7,930 kg/m³ while SS316 has a slightly higher density of 8,000 kg/m³. SS316 is heavier due to its higher molybdenum content which provides better corrosion resistance."
  },
  {
    question: "How much does a 10mm steel bar weigh per meter?",
    answer: "A 10mm MS steel round bar weighs approximately 0.617 kg per meter. This is calculated as: π × (0.005)² × 1 × 7850 = 0.617 kg/m"
  },
  {
    question: "How do I convert steel weight from kg to tons?",
    answer: "To convert steel weight from kilograms to metric tons, divide by 1000. For example, 5000 kg = 5 metric tons. For conversion to imperial tons, divide kg by 907.185."
  },
  {
    question: "Why do I need to know steel weight for procurement?",
    answer: "Steel is typically priced per kilogram. Knowing the exact weight helps you: 1) Get accurate price quotes, 2) Calculate transportation costs, 3) Verify delivery quantities, 4) Plan storage requirements."
  }
];

const relatedTools = [
  {
    title: "Pipe Weight Calculator",
    href: "/tools/pipe-weight-calculator",
    description: "Calculate hollow pipe and tube weight for various materials and dimensions."
  },
  {
    title: "Plate Weight Calculator",
    href: "/tools/plate-weight-calculator",
    description: "Calculate flat plate and sheet metal weight based on thickness and dimensions."
  },
  {
    title: "Round Bar Calculator",
    href: "/tools/round-bar-weight-calculator",
    description: "Specialized calculator for solid round bar weight calculations."
  }
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Steel Weight Calculator",
  "description": "Free online calculator to compute steel weight for round bars, pipes, plates and sheets. Supports MS Steel, SS304, SS316, Aluminum and Copper.",
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

export default function SteelWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Steel Weight Calculator"
      pageDescription="Calculate steel weight instantly"
      h1Title="Steel Weight Calculator"
      h1Subtitle="Calculate weight of MS steel, stainless steel, round bars, pipes, and plates instantly. Connect with verified steel suppliers across India."
      defaultMaterial="MS Steel"
      defaultShape="round_bar"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Steel Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
