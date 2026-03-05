'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Beam Weight</h2>
    <p className="text-gray-600 mb-6">
      I-Beams and H-Beams are essential structural members used in construction, bridges, and industrial buildings.
      Their distinctive shape provides excellent load-bearing capacity with efficient material usage.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Beam Weight Formula</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Formula</h4>
      <code className="text-blue-700">Weight = [2 × W × tf + (H - 2tf) × tw] × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">Where H = total height, W = flange width, tw = web thickness, tf = flange thickness</p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">I-Beam vs H-Beam</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">I-Beam (ISMB/IPE)</h4>
        <p className="text-sm text-gray-600">
          Height is greater than flange width. Tapered flanges. Better for bending loads.
          Common designations: ISMB 100, 150, 200, 250, 300, 400, 450, 500, 600.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">H-Beam (ISHB/HE/UC)</h4>
        <p className="text-sm text-gray-600">
          Flange width is equal to or close to height. Parallel flanges. Better for columns.
          Common designations: ISHB 150, 200, 225, 250, 300, 350, 400.
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Standard ISMB Sizes (Indian Standard Medium Weight Beam)</h3>
    <div className="bg-gray-50 rounded-lg p-4 mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2 font-semibold">Designation</th>
            <th className="text-center py-2 font-semibold">Height (mm)</th>
            <th className="text-center py-2 font-semibold">Flange (mm)</th>
            <th className="text-right py-2 font-semibold">Weight (kg/m)</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td className="py-2">ISMB 100</td><td className="text-center">100</td><td className="text-center">75</td><td className="text-right">11.5</td></tr>
          <tr className="border-b"><td className="py-2">ISMB 150</td><td className="text-center">150</td><td className="text-center">80</td><td className="text-right">14.9</td></tr>
          <tr className="border-b"><td className="py-2">ISMB 200</td><td className="text-center">200</td><td className="text-center">100</td><td className="text-right">25.4</td></tr>
          <tr className="border-b"><td className="py-2">ISMB 300</td><td className="text-center">300</td><td className="text-center">140</td><td className="text-right">46.0</td></tr>
          <tr className="border-b"><td className="py-2">ISMB 400</td><td className="text-center">400</td><td className="text-center">140</td><td className="text-right">61.5</td></tr>
          <tr><td className="py-2">ISMB 600</td><td className="text-center">600</td><td className="text-center">210</td><td className="text-right">122.6</td></tr>
        </tbody>
      </table>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Applications</h3>
    <ul className="list-disc list-inside space-y-2 text-gray-600 mb-6">
      <li><strong>Building Construction:</strong> Floor beams, roof beams, lintels</li>
      <li><strong>Industrial Structures:</strong> Crane beams, gantry structures</li>
      <li><strong>Bridges:</strong> Main girders, cross beams</li>
      <li><strong>Platforms:</strong> Mezzanine floors, walkways</li>
    </ul>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of ISMB 200 Beam:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Total Height: 200 mm</li>
        <li>Flange Width: 100 mm</li>
        <li>Web Thickness: 5.7 mm</li>
        <li>Flange Thickness: 10.8 mm</li>
        <li>Length: 6 meters</li>
      </ul>
      <p className="mt-3 font-medium">
        Flange Area = 2 × 100 × 10.8 = 2,160 mm²<br />
        Web Area = (200 - 2×10.8) × 5.7 = 1,017.8 mm²<br />
        Total Area = 3,177.8 mm² = 0.003178 m²<br />
        Weight = 0.003178 × 6 × 7,850 = <strong>149.66 kg per piece</strong>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "What is the difference between I-beam and H-beam?",
    answer: "I-beams have a height greater than flange width and tapered flanges, optimized for bending loads. H-beams have flanges nearly equal to height with parallel flanges, better for compression (columns). H-beams also have thicker web and flanges."
  },
  {
    question: "What does ISMB stand for?",
    answer: "ISMB stands for Indian Standard Medium Weight Beam. It's a standard specification as per IS 808 for I-section beams. Similarly, ISHB is Indian Standard Heavy Weight Beam with wider flanges."
  },
  {
    question: "How much does ISMB 200 weigh per meter?",
    answer: "ISMB 200 (200 × 100 × 5.7/10.8) weighs approximately 25.4 kg per meter according to IS 808 standards. For a standard 12-meter piece, the total weight is about 305 kg."
  },
  {
    question: "What is the standard length for steel beams in India?",
    answer: "Standard lengths for steel beams in India are typically 10 meters or 12 meters. Shorter lengths of 6 meters are also available. Custom cutting is possible at additional cost."
  },
  {
    question: "How do I choose between I-beam and H-beam?",
    answer: "Choose I-beam for: horizontal beams, floor supports, roof purlins. Choose H-beam for: columns, vertical members, heavy compression loads. H-beams distribute load more evenly due to equal flange width."
  },
  {
    question: "What is the moment of inertia in beam selection?",
    answer: "Moment of inertia (I) measures a beam's resistance to bending. Higher I means less deflection under load. For beams, the strong axis (Ixx) is used for typical horizontal orientation with load on top."
  }
];

const relatedTools = [
  {
    title: "Channel Weight Calculator",
    href: "/tools/channel-weight-calculator",
    description: "Calculate C-channel section weight for structural applications."
  },
  {
    title: "Angle Weight Calculator",
    href: "/tools/angle-weight-calculator",
    description: "Calculate L-angle weight for construction and fabrication."
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
  "name": "Beam Weight Calculator",
  "description": "Free online calculator to compute I-beam and H-beam weight for ISMB, ISHB sections. Supports MS Steel and other materials.",
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

export default function BeamWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Beam Weight Calculator"
      pageDescription="Calculate I-beam and H-beam weight instantly"
      h1Title="Beam Weight Calculator"
      h1Subtitle="Calculate weight of I-beams (ISMB) and H-beams (ISHB). Support for MS Steel and all standard structural beam sizes."
      defaultMaterial="MS Steel"
      defaultShape="i_beam"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Steel Beam Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
