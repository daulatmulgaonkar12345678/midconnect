'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Angle Weight</h2>
    <p className="text-gray-600 mb-6">
      L-Angles (also called angle iron or angle steel) are L-shaped structural members used extensively in construction, 
      fabrication, and manufacturing. They come in equal and unequal leg configurations.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Angle Weight Formula</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Formula</h4>
      <code className="text-blue-700">Weight = t × (A + B - t) × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">Where t = thickness, A = Leg A, B = Leg B, L = length, ρ = density</p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Types of Angles</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Equal Angle</h4>
        <p className="text-sm text-gray-600">
          Both legs have the same length. Common sizes: 25×25, 30×30, 40×40, 50×50, 65×65, 75×75, 100×100 mm.
          Thickness ranges from 3mm to 12mm depending on size.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Unequal Angle</h4>
        <p className="text-sm text-gray-600">
          Legs have different lengths. Common sizes: 40×25, 50×30, 65×45, 75×50, 100×65, 125×75 mm.
          Used when loading is asymmetric.
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Applications</h3>
    <ul className="list-disc list-inside space-y-2 text-gray-600 mb-6">
      <li><strong>Structural Frames:</strong> Building frames, trusses, and supports</li>
      <li><strong>Brackets & Supports:</strong> Shelf brackets, equipment mounts</li>
      <li><strong>Fabrication:</strong> Frames, enclosures, machine guards</li>
      <li><strong>Construction:</strong> Lintels, corner protection, edge guards</li>
    </ul>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Standard Indian Angle Sizes (ISA)</h3>
    <div className="bg-gray-50 rounded-lg p-4 mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2 font-semibold">Size (mm)</th>
            <th className="text-center py-2 font-semibold">Thickness (mm)</th>
            <th className="text-right py-2 font-semibold">Weight (kg/m)</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td className="py-2">50 × 50</td><td className="text-center">5</td><td className="text-right">3.77</td></tr>
          <tr className="border-b"><td className="py-2">65 × 65</td><td className="text-center">6</td><td className="text-right">5.80</td></tr>
          <tr className="border-b"><td className="py-2">75 × 75</td><td className="text-center">6</td><td className="text-right">6.80</td></tr>
          <tr className="border-b"><td className="py-2">100 × 100</td><td className="text-center">8</td><td className="text-right">12.10</td></tr>
          <tr><td className="py-2">150 × 150</td><td className="text-center">12</td><td className="text-right">27.30</td></tr>
        </tbody>
      </table>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel 65×65×6 Angle:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Leg A: 65 mm (0.065 m)</li>
        <li>Leg B: 65 mm (0.065 m)</li>
        <li>Thickness: 6 mm (0.006 m)</li>
        <li>Length: 6 meters</li>
      </ul>
      <p className="mt-3 font-medium">
        Area = 0.006 × (0.065 + 0.065 - 0.006) = 0.000744 m²<br />
        Volume = 0.000744 × 6 = 0.004464 m³<br />
        Weight = 0.004464 × 7,850 = <strong>35.04 kg per piece</strong>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "What is the difference between equal and unequal angle?",
    answer: "Equal angles have both legs of the same length (e.g., 50×50mm), while unequal angles have different leg lengths (e.g., 75×50mm). Equal angles are used for symmetric loads, while unequal angles are used when the loading direction is known."
  },
  {
    question: "How is angle steel thickness measured?",
    answer: "Angle thickness is uniform across both legs and is measured perpendicular to the leg surface. Standard thicknesses range from 3mm to 12mm for small angles and up to 20mm for large structural angles."
  },
  {
    question: "What is ISA in angle designation?",
    answer: "ISA stands for Indian Standard Angle. It's a designation system used in India following IS 808 standards. For example, ISA 100×100×8 means an equal angle with 100mm legs and 8mm thickness."
  },
  {
    question: "How much does a 50×50×5 angle weigh per meter?",
    answer: "A 50×50×5mm MS steel equal angle weighs approximately 3.77 kg per meter. For a standard 6-meter length, the total weight is about 22.6 kg."
  },
  {
    question: "What steel grade is used for structural angles?",
    answer: "Common steel grades for angles include MS Steel (IS 2062 E250), high strength steel (IS 2062 E350), and stainless steel grades like SS304 and SS316 for corrosion resistance applications."
  },
  {
    question: "Why do we subtract thickness in the angle formula?",
    answer: "The formula t × (A + B - t) accounts for the overlap at the corner where both legs meet. Without subtracting thickness, we would count the corner area twice, leading to overestimated weight."
  }
];

const relatedTools = [
  {
    title: "Channel Weight Calculator",
    href: "/tools/channel-weight-calculator",
    description: "Calculate C-channel section weight for structural applications."
  },
  {
    title: "Beam Weight Calculator",
    href: "/tools/beam-weight-calculator",
    description: "Calculate I-beam and H-beam weight for construction projects."
  },
  {
    title: "Steel Weight Calculator",
    href: "/tools/steel-weight-calculator",
    description: "General steel weight calculator for all shapes."
  }
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Angle Weight Calculator",
  "description": "Free online calculator to compute L-angle steel weight for equal and unequal angles. Supports MS Steel, SS304, SS316 and other materials.",
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

export default function AngleWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Angle Weight Calculator"
      pageDescription="Calculate L-angle section weight instantly"
      h1Title="Angle Weight Calculator"
      h1Subtitle="Calculate weight of equal and unequal L-angles. Support for MS Steel, SS304, SS316 and all standard ISA sizes."
      defaultMaterial="MS Steel"
      defaultShape="angle"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Angle Steel Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
