'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Plate Weight</h2>
    <p className="text-gray-600 mb-6">
      Steel plate weight calculation is straightforward - it's simply the volume multiplied by density. 
      The volume is calculated as thickness × width × length. This applies to all flat metal products 
      including plates, sheets, and coils.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Plate Weight Formula</h3>
    <div className="bg-orange-50 rounded-lg p-4 border border-orange-200 mb-6">
      <h4 className="font-semibold text-orange-800 mb-2">Standard Plate Weight Formula</h4>
      <code className="text-orange-700 text-lg">Weight = Thickness × Width × Length × Density</code>
      <p className="text-sm text-orange-600 mt-2">
        All dimensions in meters, density in kg/m³
      </p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Plate vs Sheet: What's the Difference?</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">Steel Plates</h4>
        <p className="text-sm text-gray-600">
          Thickness: 6mm and above<br />
          Used in: Construction, shipbuilding, heavy machinery<br />
          Typically cut to custom sizes
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">Steel Sheets</h4>
        <p className="text-sm text-gray-600">
          Thickness: Below 6mm<br />
          Used in: Automotive, appliances, roofing<br />
          Available in standard sizes or coils
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Plate Types</h3>
    <div className="space-y-3 mb-6">
      <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="font-semibold text-gray-800 min-w-[120px]">MS Plates</span>
        <span className="text-gray-600">General construction, structural applications</span>
      </div>
      <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="font-semibold text-gray-800 min-w-[120px]">HR Plates</span>
        <span className="text-gray-600">Hot Rolled plates for structural work</span>
      </div>
      <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="font-semibold text-gray-800 min-w-[120px]">CR Sheets</span>
        <span className="text-gray-600">Cold Rolled for smooth finish applications</span>
      </div>
      <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="font-semibold text-gray-800 min-w-[120px]">Chequered</span>
        <span className="text-gray-600">Anti-slip surface for flooring, steps</span>
      </div>
      <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
        <span className="font-semibold text-gray-800 min-w-[120px]">SS Plates</span>
        <span className="text-gray-600">Stainless steel for corrosion resistance</span>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel Plate:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Thickness: 10 mm (0.01 m)</li>
        <li>Width: 1250 mm (1.25 m)</li>
        <li>Length: 2500 mm (2.5 m)</li>
        <li>Density: 7,850 kg/m³</li>
      </ul>
      <p className="mt-3">
        Volume = 0.01 × 1.25 × 2.5 = 0.03125 m³<br />
        Weight = 0.03125 × 7,850 = <strong>245.3 kg per plate</strong>
      </p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">Standard Plate Sizes in India</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
      <p className="text-gray-700 mb-2">Common standard sizes available:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600 text-sm">
        <li>1250 × 2500 mm (Standard)</li>
        <li>1500 × 3000 mm (Large)</li>
        <li>1250 × 6000 mm (Long)</li>
        <li>Custom sizes available on order</li>
      </ul>
    </div>
  </>
);

const faqs = [
  {
    question: "How do you calculate steel plate weight?",
    answer: "Steel plate weight is calculated using: Weight = Thickness × Width × Length × Density. For MS steel, use density 7,850 kg/m³. Ensure all dimensions are in meters for correct results."
  },
  {
    question: "What is the weight of 10mm MS plate per square meter?",
    answer: "A 10mm thick MS steel plate weighs approximately 78.5 kg per square meter. This is calculated as: 0.01m × 1m × 1m × 7850 kg/m³ = 78.5 kg/m²."
  },
  {
    question: "What is the difference between HR and CR plates?",
    answer: "HR (Hot Rolled) plates are processed at high temperatures and have a rough surface. CR (Cold Rolled) plates are processed at room temperature, resulting in a smoother finish and tighter tolerances but are typically thinner."
  },
  {
    question: "How much does a standard 1250×2500mm steel plate weigh?",
    answer: "The weight depends on thickness. A 6mm plate weighs about 147 kg, 10mm weighs about 245 kg, and 20mm weighs about 490 kg. Use our calculator for exact weights."
  },
  {
    question: "What is chequered plate and how is its weight calculated?",
    answer: "Chequered plate has a raised pattern (tears or diamonds) for anti-slip properties. Weight calculation uses the base thickness, not including the pattern. Add approximately 5-10% extra for the pattern weight."
  },
  {
    question: "How do I calculate weight for circular plates?",
    answer: "For circular plates: Weight = π × (diameter/2)² × thickness × density. For example, a 1m diameter, 10mm thick MS plate weighs: 3.14159 × 0.5² × 0.01 × 7850 = 61.7 kg."
  }
];

const relatedTools = [
  {
    title: "Steel Weight Calculator",
    href: "/tools/steel-weight-calculator",
    description: "Calculate weight for all types of steel products including bars and pipes."
  },
  {
    title: "Pipe Weight Calculator",
    href: "/tools/pipe-weight-calculator",
    description: "Calculate hollow pipe and tube weight using OD and wall thickness."
  },
  {
    title: "Round Bar Calculator",
    href: "/tools/round-bar-weight-calculator",
    description: "Calculate solid round bar weight for different materials and sizes."
  }
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Plate Weight Calculator",
  "description": "Free online calculator to compute steel plate and sheet weight based on thickness, width, and length. Supports MS Steel, Stainless Steel, and other materials.",
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

export default function PlateWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Plate Weight Calculator"
      pageDescription="Calculate plate weight instantly"
      h1Title="Plate Weight Calculator"
      h1Subtitle="Calculate weight of MS plates, SS plates, chequered plates, and sheet metal using thickness and dimensions. Connect with verified plate suppliers."
      defaultMaterial="MS Steel"
      defaultShape="plate"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Plate Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
