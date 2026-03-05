'use client';

import SEOCalculatorLayout from '@/components/seo/SEOCalculatorLayout';

const educationalContent = (
  <>
    <h2 className="text-2xl font-bold text-gray-900 mb-4">How to Calculate Pipe Weight</h2>
    <p className="text-gray-600 mb-6">
      Pipe weight calculation requires knowing the outer diameter (OD), wall thickness, length, and material density. 
      Unlike solid bars, pipes are hollow, so we calculate the volume of the metal shell only.
    </p>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Pipe Weight Formula</h3>
    <div className="bg-purple-50 rounded-lg p-4 border border-purple-200 mb-6">
      <h4 className="font-semibold text-purple-800 mb-2">Standard Pipe Weight Calculation</h4>
      <code className="text-purple-700 text-lg">Weight = π × ((OD/2)² - (ID/2)²) × L × ρ</code>
      <p className="text-sm text-purple-600 mt-2">
        Where: OD = Outer Diameter, ID = Inner Diameter (OD - 2×thickness), L = Length, ρ = Density
      </p>
    </div>

    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200 mb-6">
      <h4 className="font-semibold text-blue-800 mb-2">Simplified Formula</h4>
      <code className="text-blue-700">Weight = π × (OD - t) × t × L × ρ</code>
      <p className="text-sm text-blue-600 mt-2">
        Where: OD = Outer Diameter, t = Wall Thickness, L = Length, ρ = Density
      </p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Common Pipe Types</h3>
    <div className="grid md:grid-cols-2 gap-4 mb-6">
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">Seamless Pipes</h4>
        <p className="text-sm text-gray-600">
          Made without welded seams, offering uniform strength throughout. Used in high-pressure applications.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">ERW Pipes</h4>
        <p className="text-sm text-gray-600">
          Electric Resistance Welded pipes, cost-effective for low-to-medium pressure applications.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">GI Pipes</h4>
        <p className="text-sm text-gray-600">
          Galvanized Iron pipes with zinc coating for corrosion resistance. Common in water supply.
        </p>
      </div>
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2">SS Pipes</h4>
        <p className="text-sm text-gray-600">
          Stainless Steel pipes for chemical, food, and pharmaceutical industries.
        </p>
      </div>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3">Example Calculation</h3>
    <div className="bg-gray-50 rounded-lg p-4">
      <p className="font-medium mb-2">Calculate weight of MS Steel Pipe:</p>
      <ul className="list-disc list-inside space-y-1 text-gray-600">
        <li>Outer Diameter (OD): 50 mm (0.05 m)</li>
        <li>Wall Thickness: 3 mm (0.003 m)</li>
        <li>Length: 6 meters</li>
        <li>Density: 7,850 kg/m³</li>
      </ul>
      <p className="mt-3">
        Inner Diameter (ID) = 50 - (2 × 3) = 44 mm (0.044 m)<br />
        Volume = π × ((0.025)² - (0.022)²) × 6 = 0.00266 m³<br />
        Weight = 0.00266 × 7,850 = <strong>20.9 kg per piece</strong>
      </p>
    </div>

    <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">Standard Pipe Schedules</h3>
    <p className="text-gray-600 mb-4">
      Pipes are manufactured in standard schedules (SCH) that define wall thickness. 
      Common schedules include SCH 10, SCH 40, SCH 80, and SCH 160. Higher schedule numbers indicate thicker walls.
    </p>
  </>
);

const faqs = [
  {
    question: "How do you calculate pipe weight from OD and thickness?",
    answer: "Pipe weight is calculated using: Weight = π × (OD - thickness) × thickness × length × density. For example, a 50mm OD pipe with 3mm thickness and 6m length in MS steel weighs approximately 20.9 kg."
  },
  {
    question: "What is the difference between seamless and ERW pipes?",
    answer: "Seamless pipes are manufactured without any welded seam, making them stronger and suitable for high-pressure applications. ERW (Electric Resistance Welded) pipes have a welded seam and are more cost-effective for general applications."
  },
  {
    question: "How much does a 2-inch steel pipe weigh per meter?",
    answer: "A 2-inch (nominal) Schedule 40 steel pipe weighs approximately 3.65 kg per meter. The exact weight depends on the schedule (wall thickness) - Schedule 80 would be heavier at about 5.4 kg/m."
  },
  {
    question: "What is pipe schedule and how does it affect weight?",
    answer: "Pipe schedule (SCH) is a standardized wall thickness designation. Higher schedules mean thicker walls and heavier pipes. SCH 40 is standard weight, SCH 80 is extra strong, and SCH 160 is double extra strong."
  },
  {
    question: "How do I convert pipe nominal size to actual dimensions?",
    answer: "Nominal Pipe Size (NPS) is not the actual measurement. For example, a 2-inch NPS pipe has an OD of 60.3mm. You need to refer to pipe dimension charts to get actual OD and ID values for weight calculations."
  },
  {
    question: "Why is inner diameter important for pipe weight?",
    answer: "The inner diameter determines the hollow space inside the pipe. The weight is calculated from the metal volume only (outer area minus inner area). A pipe with larger ID (thinner wall) will weigh less than one with smaller ID."
  }
];

const relatedTools = [
  {
    title: "Steel Weight Calculator",
    href: "/tools/steel-weight-calculator",
    description: "Calculate weight for all types of steel products including bars, plates, and sheets."
  },
  {
    title: "Plate Weight Calculator",
    href: "/tools/plate-weight-calculator",
    description: "Calculate flat plate and sheet metal weight based on thickness and dimensions."
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
  "name": "Pipe Weight Calculator",
  "description": "Free online calculator to compute pipe weight based on outer diameter, wall thickness, and length. Supports MS Steel, Stainless Steel, and other materials.",
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

export default function PipeWeightCalculatorClient() {
  return (
    <SEOCalculatorLayout
      pageTitle="Pipe Weight Calculator"
      pageDescription="Calculate pipe weight instantly"
      h1Title="Pipe Weight Calculator"
      h1Subtitle="Calculate weight of MS pipes, SS pipes, seamless pipes, and ERW pipes using outer diameter and wall thickness. Connect with verified pipe suppliers."
      defaultMaterial="MS Steel"
      defaultShape="pipe"
      educationalContent={educationalContent}
      faqs={faqs}
      relatedTools={relatedTools}
      supplierSectionTitle="Find Pipe Suppliers in India"
      jsonLd={jsonLd}
    />
  );
}
