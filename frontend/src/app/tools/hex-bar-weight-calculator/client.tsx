'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Hex Bar Weight</h2>
    <p className="text-gray-600 mb-6">
      Hexagonal bars (hex bars) are commonly used in manufacturing bolts, nuts, and precision components.
      The weight calculation requires the "Across Flats" (AF) dimension, which is the distance between two parallel flat sides.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Hex Bar Weight Formula</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Formula</h4>
      <code className="text-blue-700">Weight = (√3/2) × AF² × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">Where AF = Across Flats, L = length, ρ = density</p>
      <p className="text-sm text-blue-600 mt-1">Simplified: Weight ≈ 0.866 × AF² × L × ρ</p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Understanding Hex Bar Dimensions</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Across Flats (AF)</h4>
        <p className="text-sm text-gray-600">
          The distance between two parallel flat sides. This is the standard way hex bars are specified.
          Common sizes: 10mm, 12mm, 16mm, 19mm, 22mm, 25mm, 32mm, 36mm, 41mm.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">Across Corners (AC)</h4>
        <p className="text-sm text-gray-600">
          The distance between two opposite corners. If you only have AC, convert to AF using:
          AF = AC × cos(30°) = AC × 0.866
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Hex Bar Applications</h3>
    <ul className="list-disc list-inside space-y-2 text-gray-600 mb-6">
      <li><strong>Fasteners:</strong> Bolts, nuts, and studs</li>
      <li><strong>Machine Components:</strong> Shafts, spindles, and tool holders</li>
      <li><strong>Structural:</strong> Hexagonal columns and supports</li>
      <li><strong>Precision Parts:</strong> CNC machined components</li>
    </ul>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel Hex Bar:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Across Flats: 25 mm (0.025 m)</li>
        <li>Length: 3 meters</li>
        <li>Density: 7,850 kg/m³</li>
      </ul>
      <p className="mt-3 font-medium">
        Area = 0.866 × (0.025)² = 0.000541 m²<br />
        Volume = 0.000541 × 3 = 0.001623 m³<br />
        Weight = 0.001623 × 7,850 = <strong>12.74 kg per piece</strong>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "What is 'Across Flats' (AF) in hex bar measurement?",
    answer: "Across Flats (AF) is the distance between two parallel flat sides of a hexagonal bar. It's the standard measurement used to specify hex bar sizes. For example, a 25mm hex bar has an AF of 25mm."
  },
  {
    question: "How do I convert Across Corners to Across Flats?",
    answer: "To convert Across Corners (AC) to Across Flats (AF), multiply by 0.866 (or cos 30°). Formula: AF = AC × 0.866. For example, if AC = 30mm, then AF = 30 × 0.866 = 25.98mm ≈ 26mm."
  },
  {
    question: "What materials are hex bars available in?",
    answer: "Hex bars are available in various materials including MS Steel, EN8, EN19, SS304, SS316, Aluminum 6061/6063, Brass, and Copper. Each material has different mechanical properties suitable for specific applications."
  },
  {
    question: "Why are hex bars used instead of round bars?",
    answer: "Hex bars are preferred when: 1) The part needs to be held firmly in a chuck without slipping, 2) A wrench grip surface is needed (like bolt heads), 3) Manufacturing hexagonal shapes is required, 4) Better material utilization when machining hex shapes."
  },
  {
    question: "What is the weight of a 19mm hex bar per meter in MS steel?",
    answer: "A 19mm (AF) MS steel hex bar weighs approximately 2.13 kg per meter. Calculation: 0.866 × (0.019)² × 1 × 7850 = 2.13 kg/m"
  },
  {
    question: "How accurate is the hex bar weight calculator?",
    answer: "Our calculator provides theoretical weights based on standard material densities. Actual weights may vary by ±2-3% due to manufacturing tolerances, surface finish, and material composition variations."
  }
];

const relatedTools = [
  {
    title: "Round Bar Calculator",
    href: "/tools/round-bar-weight-calculator",
    description: "Calculate solid round bar weight for various materials and dimensions."
  },
  {
    title: "Steel Weight Calculator",
    href: "/tools/steel-weight-calculator",
    description: "General steel weight calculator for all shapes including bars, pipes, and plates."
  },
  {
    title: "Angle Weight Calculator",
    href: "/tools/angle-weight-calculator",
    description: "Calculate L-angle weight for structural applications."
  }
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "Hex Bar Weight Calculator",
  "description": "Free online calculator to compute hexagonal bar weight using across flats dimension. Supports MS Steel, SS304, SS316, Aluminum and other materials.",
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

export default function HexBarWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Hex Bar Weight Calculator"
      pageDescription="Calculate hexagonal bar weight instantly"
      h1Title="Hex Bar Weight Calculator"
      h1Subtitle="Calculate weight of hexagonal bars using across flats dimension. Support for MS Steel, SS304, SS316, Aluminum and more."
      defaultMaterial="MS Steel"
      defaultShape="hex_bar"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Hex Bar Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
