'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Channel Weight</h2>
    <p className="text-gray-600 mb-6">
      C-Channels (also called channel sections or steel channels) are C-shaped structural members widely used in construction
      and fabrication. They provide excellent strength-to-weight ratio for beams, supports, and framing.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Channel Weight Formula</h3>
    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Formula</h4>
      <code className="text-blue-700">Weight = [(H-2tf) × tw + 2 × W × tf] × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">Where H = web height, W = flange width, tw = web thickness, tf = flange thickness</p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Channel Designations in India</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">ISMC (Indian Standard Medium Channel)</h4>
        <p className="text-sm text-gray-600">
          Medium weight channels for general structural use. Common sizes: ISMC 75, 100, 125, 150, 175, 200, 250, 300.
          Web thickness typically 4-8mm.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold mb-2">ISLC (Indian Standard Light Channel)</h4>
        <p className="text-sm text-gray-600">
          Lighter channels for non-critical applications. Lower web and flange thickness compared to ISMC.
          Used where weight savings are important.
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Standard ISMC Sizes</h3>
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
          <tr className="border-b"><td className="py-2">ISMC 75</td><td className="text-center">75</td><td className="text-center">40</td><td className="text-right">6.8</td></tr>
          <tr className="border-b"><td className="py-2">ISMC 100</td><td className="text-center">100</td><td className="text-center">50</td><td className="text-right">9.6</td></tr>
          <tr className="border-b"><td className="py-2">ISMC 150</td><td className="text-center">150</td><td className="text-center">75</td><td className="text-right">16.4</td></tr>
          <tr className="border-b"><td className="py-2">ISMC 200</td><td className="text-center">200</td><td className="text-center">75</td><td className="text-right">22.1</td></tr>
          <tr><td className="py-2">ISMC 300</td><td className="text-center">300</td><td className="text-center">90</td><td className="text-right">36.3</td></tr>
        </tbody>
      </table>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Applications</h3>
    <ul className="list-disc list-inside space-y-2 text-gray-600 mb-6">
      <li><strong>Purlins & Girts:</strong> Roof and wall support in pre-engineered buildings</li>
      <li><strong>Framing:</strong> Door/window frames, equipment frames</li>
      <li><strong>Conveyor Systems:</strong> Support structures for material handling</li>
      <li><strong>Stairs & Platforms:</strong> Stringers and support members</li>
    </ul>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of ISMC 150 Channel:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Web Height: 150 mm</li>
        <li>Flange Width: 75 mm</li>
        <li>Web Thickness: 5.4 mm</li>
        <li>Flange Thickness: 9 mm</li>
        <li>Length: 6 meters</li>
      </ul>
      <p className="mt-3 font-medium">
        Web Area = (150 - 2×9) × 5.4 = 712.8 mm²<br />
        Flange Area = 2 × 75 × 9 = 1,350 mm²<br />
        Total Area = 2,062.8 mm² = 0.002063 m²<br />
        Weight = 0.002063 × 6 × 7,850 = <strong>97.16 kg per piece</strong>
      </p>
    </div>
  </>
);

const faqs = [
  {
    question: "What is the difference between ISMC and ISLC channels?",
    answer: "ISMC (Indian Standard Medium Channel) has thicker web and flanges compared to ISLC (Light Channel). ISMC is used for structural applications requiring higher load capacity, while ISLC is suitable for lighter loads and non-critical applications."
  },
  {
    question: "How do I specify a channel section?",
    answer: "Channels are typically specified by designation (e.g., ISMC 150) which indicates the web height in mm. Full specification includes: ISMC 150 × 75 × 5.4/9 meaning 150mm height, 75mm flange, 5.4mm web thickness, 9mm flange thickness."
  },
  {
    question: "What is the standard length for steel channels in India?",
    answer: "Standard lengths for steel channels in India are typically 6 meters, 9 meters, or 12 meters. Custom lengths can be cut to size by steel suppliers."
  },
  {
    question: "How much does ISMC 150 weigh per meter?",
    answer: "ISMC 150 (150 × 75 × 5.4/9) weighs approximately 16.4 kg per meter according to IS 808 standards. For a standard 6-meter piece, the total weight is about 98.4 kg."
  },
  {
    question: "Can channels be used as beams?",
    answer: "Yes, channels can be used as beams for moderate loads. For heavy-duty beam applications, I-beams or H-beams are preferred due to their symmetric cross-section and higher moment of inertia."
  },
  {
    question: "What is the web and flange in a channel section?",
    answer: "The web is the vertical portion connecting the two flanges. The flanges are the two horizontal legs at top and bottom. Web thickness is usually less than flange thickness for most standard channels."
  }
];

const relatedTools = [
  {
    title: "Beam Weight Calculator",
    href: "/tools/beam-weight-calculator",
    description: "Calculate I-beam and H-beam weight for structural applications."
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
  "name": "Channel Weight Calculator",
  "description": "Free online calculator to compute C-channel steel weight for ISMC and ISLC sections. Supports MS Steel, SS304, SS316 and other materials.",
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

export default function ChannelWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Channel Weight Calculator"
      pageDescription="Calculate C-channel section weight instantly"
      h1Title="Channel Weight Calculator"
      h1Subtitle="Calculate weight of ISMC and ISLC channel sections. Support for MS Steel, SS304, SS316 and all standard sizes."
      defaultMaterial="MS Steel"
      defaultShape="channel"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Channel Steel Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
