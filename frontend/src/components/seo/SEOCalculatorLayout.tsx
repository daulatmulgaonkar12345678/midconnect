'use client';

import { useState, ReactNode } from 'react';
import Link from 'next/link';
import { Calculator, Scale, ChevronDown, ChevronUp, ExternalLink, ArrowRight } from 'lucide-react';
import MaterialCalculatorCard, { CalculationResult } from '@/components/calculator/MaterialCalculatorCard';

interface FAQ {
  question: string;
  answer: string;
}

interface RelatedTool {
  title: string;
  href: string;
  description: string;
}

interface SEOCalculatorLayoutProps {
  // SEO metadata
  pageTitle: string;
  pageDescription: string;
  h1Title: string;
  h1Subtitle: string;
  
  // Calculator defaults
  defaultMaterial?: string;
  defaultShape?: string;
  
  // Content
  educationalContent: ReactNode;
  faqs: FAQ[];
  relatedTools: RelatedTool[];
  
  // Optional: Custom supplier section title
  supplierSectionTitle?: string;
  
  // JSON-LD data
  jsonLd: object;
}

// FAQ Item component with collapsible functionality
function FAQItem({ faq, index, isOpen, onToggle }: { 
  faq: FAQ; 
  index: number; 
  isOpen: boolean; 
  onToggle: () => void; 
}) {
  return (
    <div className="border-b border-gray-200 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full py-4 flex items-center justify-between text-left hover:bg-gray-50 transition"
        aria-expanded={isOpen}
        data-testid={`faq-${index}`}
      >
        <span className="font-medium text-gray-900 pr-4">{faq.question}</span>
        {isOpen ? (
          <ChevronUp className="h-5 w-5 text-gray-500 flex-shrink-0" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-500 flex-shrink-0" />
        )}
      </button>
      {isOpen && (
        <div className="pb-4 text-gray-600 leading-relaxed">
          {faq.answer}
        </div>
      )}
    </div>
  );
}

export default function SEOCalculatorLayout({
  pageTitle,
  pageDescription,
  h1Title,
  h1Subtitle,
  defaultMaterial = 'MS Steel',
  defaultShape = 'round_bar',
  educationalContent,
  faqs,
  relatedTools,
  supplierSectionTitle = 'Find Verified Suppliers',
  jsonLd,
}: SEOCalculatorLayoutProps) {
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  const handleCalculation = (result: CalculationResult) => {
    setCalculationResult(result);
  };

  // Generate FAQ schema
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": faqs.map(faq => ({
      "@type": "Question",
      "name": faq.question,
      "acceptedAnswer": {
        "@type": "Answer",
        "text": faq.answer
      }
    }))
  };

  return (
    <>
      {/* JSON-LD Structured Data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />

      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-40">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center gap-2">
                <div className="p-2 bg-blue-600 rounded-lg">
                  <Calculator className="h-5 w-5 text-white" />
                </div>
                <span className="font-bold text-xl text-gray-900">UdyogConnect</span>
              </Link>
              <nav className="hidden md:flex items-center gap-6 text-sm">
                <Link href="/tools/steel-weight-calculator" className="text-gray-600 hover:text-blue-600">Steel Calculator</Link>
                <Link href="/tools/pipe-weight-calculator" className="text-gray-600 hover:text-blue-600">Pipe Calculator</Link>
                <Link href="/tools/beam-weight-calculator" className="text-gray-600 hover:text-blue-600">Beam Calculator</Link>
                <Link href="/tools/angle-weight-calculator" className="text-gray-600 hover:text-blue-600">Angle Calculator</Link>
                <Link href="/" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                  Browse Suppliers
                </Link>
              </nav>
            </div>
          </div>
        </header>

        <main>
          {/* Hero Section */}
          <section className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white py-12 md:py-16">
            <div className="max-w-6xl mx-auto px-4 text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 rounded-full text-sm mb-6">
                <Scale className="h-4 w-4" />
                Free Online Calculator
              </div>
              <h1 className="text-3xl md:text-5xl font-bold mb-4">{h1Title}</h1>
              <p className="text-lg md:text-xl text-blue-100 max-w-2xl mx-auto">
                {h1Subtitle}
              </p>
            </div>
          </section>

          {/* Calculator Section */}
          <section className="py-8 md:py-12 -mt-8 relative z-10">
            <div className="max-w-6xl mx-auto px-4">
              <div className="grid lg:grid-cols-5 gap-8">
                {/* Calculator Card - Takes 3 columns */}
                <div className="lg:col-span-3">
                  <MaterialCalculatorCard
                    onCalculate={handleCalculation}
                    defaultMaterial={defaultMaterial}
                    defaultShape={defaultShape}
                    showPriceField={false}
                    className="shadow-xl border-2 border-white"
                  />
                </div>

                {/* Results Summary - Takes 2 columns */}
                <div className="lg:col-span-2 space-y-6">
                  {/* Calculation Result */}
                  {calculationResult && calculationResult.total_weight > 0 ? (
                    <div className="bg-white rounded-xl shadow-xl p-6 border" data-testid="calculation-result">
                      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <Scale className="h-5 w-5 text-blue-600" />
                        Your Calculation Result
                      </h2>
                      <div className="space-y-3">
                        <div className="flex justify-between items-center py-2 border-b">
                          <span className="text-gray-600">Material</span>
                          <span className="font-semibold">{calculationResult.material}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b">
                          <span className="text-gray-600">Shape</span>
                          <span className="font-semibold capitalize">{calculationResult.shape.replace('_', ' ')}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b">
                          <span className="text-gray-600">Quantity</span>
                          <span className="font-semibold">{calculationResult.quantity} pcs</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b">
                          <span className="text-gray-600">Weight per piece</span>
                          <span className="font-semibold">{calculationResult.weight_per_piece_display}</span>
                        </div>
                        <div className="flex justify-between items-center py-3 bg-blue-50 rounded-lg px-3 -mx-3">
                          <span className="text-blue-800 font-medium">Total Weight</span>
                          <span className="text-2xl font-bold text-blue-600">{calculationResult.total_weight_display}</span>
                        </div>
                      </div>

                      {/* CTA */}
                      <div className="mt-6 pt-6 border-t">
                        <p className="text-sm text-gray-600 mb-3">Get quotes from verified suppliers</p>
                        <Link
                          href="/"
                          className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
                        >
                          Find Suppliers <ArrowRight className="h-4 w-4" />
                        </Link>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white rounded-xl shadow-xl p-6 border text-center">
                      <Calculator className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-700 mb-2">Enter Dimensions</h3>
                      <p className="text-gray-500 text-sm">
                        Fill in the calculator on the left to see your weight calculation results here.
                      </p>
                    </div>
                  )}

                  {/* Quick Links */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 border border-green-200">
                    <h3 className="font-semibold text-green-800 mb-3">Why use UdyogConnect?</h3>
                    <ul className="space-y-2 text-sm text-green-700">
                      <li className="flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        Free instant weight calculations
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        Connect with verified suppliers
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        Compare prices from multiple sellers
                      </li>
                      <li className="flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">✓</span>
                        No registration required
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Suppliers Section */}
          <section className="py-12 bg-gray-50" data-testid="suppliers-section">
            <div className="max-w-6xl mx-auto px-4">
              <div className="text-center mb-8">
                <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">{supplierSectionTitle}</h2>
                <p className="text-gray-600">Connect with trusted industrial suppliers across India</p>
              </div>
              <div className="text-center">
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
                >
                  Browse All Suppliers <ExternalLink className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </section>

          {/* Educational Content Section */}
          <section className="py-12 md:py-16" data-testid="educational-content">
            <div className="max-w-4xl mx-auto px-4">
              <div className="prose prose-lg max-w-none">
                {educationalContent}
              </div>
            </div>
          </section>

          {/* FAQ Section */}
          <section className="py-12 md:py-16 bg-gray-50" data-testid="faq-section">
            <div className="max-w-3xl mx-auto px-4">
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-8 text-center">
                Frequently Asked Questions
              </h2>
              <div className="bg-white rounded-xl shadow-sm border divide-y">
                {faqs.map((faq, index) => (
                  <FAQItem
                    key={index}
                    faq={faq}
                    index={index}
                    isOpen={openFaqIndex === index}
                    onToggle={() => setOpenFaqIndex(openFaqIndex === index ? null : index)}
                  />
                ))}
              </div>
            </div>
          </section>

          {/* Related Tools Section */}
          <section className="py-12 md:py-16" data-testid="related-tools">
            <div className="max-w-6xl mx-auto px-4">
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 mb-8 text-center">
                Related Calculators
              </h2>
              <div className="grid md:grid-cols-3 gap-6">
                {relatedTools.map((tool, index) => (
                  <Link
                    key={index}
                    href={tool.href}
                    className="bg-white rounded-xl p-6 border shadow-sm hover:shadow-md hover:border-blue-300 transition group"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition">
                        <Calculator className="h-5 w-5 text-blue-600" />
                      </div>
                      <h3 className="font-semibold text-gray-900">{tool.title}</h3>
                    </div>
                    <p className="text-sm text-gray-600">{tool.description}</p>
                  </Link>
                ))}
              </div>
            </div>
          </section>
        </main>

        {/* Footer */}
        <footer className="bg-gray-900 text-white py-12">
          <div className="max-w-6xl mx-auto px-4">
            <div className="grid md:grid-cols-4 gap-8">
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="p-2 bg-blue-600 rounded-lg">
                    <Calculator className="h-5 w-5 text-white" />
                  </div>
                  <span className="font-bold text-xl">UdyogConnect</span>
                </div>
                <p className="text-gray-400 text-sm">
                  India's trusted B2B marketplace for industrial products and raw materials.
                </p>
              </div>
              <div>
                <h4 className="font-semibold mb-4">Calculators</h4>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li><Link href="/tools/steel-weight-calculator" className="hover:text-white">Steel Weight Calculator</Link></li>
                  <li><Link href="/tools/pipe-weight-calculator" className="hover:text-white">Pipe Weight Calculator</Link></li>
                  <li><Link href="/tools/plate-weight-calculator" className="hover:text-white">Plate Weight Calculator</Link></li>
                  <li><Link href="/tools/round-bar-weight-calculator" className="hover:text-white">Round Bar Calculator</Link></li>
                  <li><Link href="/tools/hex-bar-weight-calculator" className="hover:text-white">Hex Bar Calculator</Link></li>
                  <li><Link href="/tools/angle-weight-calculator" className="hover:text-white">Angle Calculator</Link></li>
                  <li><Link href="/tools/channel-weight-calculator" className="hover:text-white">Channel Calculator</Link></li>
                  <li><Link href="/tools/beam-weight-calculator" className="hover:text-white">Beam Calculator</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-4">Marketplace</h4>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li><Link href="/" className="hover:text-white">Browse Products</Link></li>
                  <li><Link href="/categories" className="hover:text-white">Categories</Link></li>
                  <li><Link href="/seller/register" className="hover:text-white">Become a Seller</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-4">Company</h4>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li><Link href="/about" className="hover:text-white">About Us</Link></li>
                  <li><Link href="/contact" className="hover:text-white">Contact</Link></li>
                  <li><Link href="/privacy" className="hover:text-white">Privacy Policy</Link></li>
                </ul>
              </div>
            </div>
            <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
              <p>&copy; {new Date().getFullYear()} UdyogConnect. All rights reserved.</p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
