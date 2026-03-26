import { Metadata } from 'next';
import Link from 'next/link';
import { Check, X, Star, Zap, Shield, Crown, Clock, ArrowRight, ChevronDown, BarChart3, Settings, Users, Boxes, FileText, MessageSquare, Layers } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Pricing - UdyogConnect',
  description: 'Simple, transparent pricing. Run your entire business from one system. Start simple and upgrade as you grow.',
};

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-10 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
          Simple, Transparent Pricing
        </h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Run your entire business from one system. Start simple and upgrade as you grow.
        </p>
      </section>

      {/* Plans */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">

          {/* Starter */}
          <div className="bg-white rounded-2xl border border-gray-200 p-7 flex flex-col" data-testid="plan-starter">
            <div className="mb-5">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-gray-100 rounded-xl mb-3">
                <Star className="h-5 w-5 text-gray-500" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Starter</h2>
              <p className="text-sm text-gray-400 mt-1">For exploring the platform</p>
            </div>
            <div className="mb-6">
              <span className="text-3xl font-bold text-gray-900">Free</span>
            </div>
            <ul className="space-y-2.5 mb-8 flex-1">
              <PlanFeature>Basic business profile</PlanFeature>
              <PlanFeature>Limited features access</PlanFeature>
              <PlanFeature>Explore system interface</PlanFeature>
              <PlanFeature>Email support</PlanFeature>
            </ul>
            <p className="text-xs text-gray-400 mb-4 italic">Best for understanding how the system works</p>
            <Link href="/register" className="block w-full text-center py-2.5 border-2 border-gray-300 text-gray-700 rounded-xl text-sm font-semibold hover:bg-gray-50 transition" data-testid="starter-cta">
              Get Started Free
            </Link>
          </div>

          {/* Standard */}
          <div className="bg-white rounded-2xl border border-blue-200 p-7 flex flex-col" data-testid="plan-standard">
            <div className="mb-5">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-blue-50 rounded-xl mb-3">
                <Zap className="h-5 w-5 text-blue-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Standard</h2>
              <p className="text-sm text-gray-400 mt-1">For businesses starting digital operations</p>
            </div>
            <div className="mb-2">
              <span className="text-3xl font-bold text-gray-900">&#8377;10,000</span>
              <span className="text-gray-400 text-sm"> / year</span>
            </div>
            <div className="mb-6 inline-flex items-center gap-1.5 bg-green-50 text-green-700 text-xs font-semibold px-2.5 py-1 rounded-full w-fit border border-green-200">
              <span>Founding Offer:</span> <span className="font-bold">&#8377;5,000</span> <span className="text-green-500">(Limited)</span>
            </div>
            <ul className="space-y-2.5 mb-5 flex-1">
              <PlanFeature>Inventory (stock) management</PlanFeature>
              <PlanFeature>Employee management</PlanFeature>
              <PlanFeature>Buyer &amp; Supplier management</PlanFeature>
              <PlanFeature>Invoice &amp; Purchase Orders</PlanFeature>
              <PlanFeature>WhatsApp integration</PlanFeature>
              <PlanFeature>Daily business tracking</PlanFeature>
              <PlanFeature>Limited custom panels</PlanFeature>
              <PlanFeature>Excel &amp; PDF exports</PlanFeature>
              <PlanFeature>Basic support</PlanFeature>
            </ul>
            <div className="mb-4 space-y-1.5">
              <PlanLimit>No automation</PlanLimit>
              <PlanLimit>Limited scalability</PlanLimit>
            </div>
            <p className="text-xs text-gray-400 mb-4 italic">Ideal for shifting from manual to digital systems</p>
            <Link href="/register" className="block w-full text-center py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold hover:bg-blue-700 transition" data-testid="standard-cta">
              Start Now
            </Link>
          </div>

          {/* Pro (Most Popular) */}
          <div className="bg-white rounded-2xl border-2 border-orange-400 p-7 flex flex-col relative shadow-lg shadow-orange-100/50" data-testid="plan-pro">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
              <span className="bg-orange-500 text-white text-xs font-bold px-4 py-1 rounded-full whitespace-nowrap">
                Most Popular
              </span>
            </div>
            <div className="mb-5">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-orange-50 rounded-xl mb-3">
                <Shield className="h-5 w-5 text-orange-500" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Pro</h2>
              <p className="text-sm text-gray-400 mt-1">Full automation and control</p>
            </div>
            <div className="mb-2">
              <span className="text-3xl font-bold text-gray-900">&#8377;15,000</span>
              <span className="text-gray-400 text-sm"> / year</span>
            </div>
            <div className="mb-6 inline-flex items-center gap-1.5 bg-green-50 text-green-700 text-xs font-semibold px-2.5 py-1 rounded-full w-fit border border-green-200">
              <span>Founding Offer:</span> <span className="font-bold">&#8377;7,500</span> <span className="text-green-500">(Limited)</span>
            </div>
            <p className="text-xs text-gray-500 font-medium mb-2">Everything in Standard, plus:</p>
            <ul className="space-y-2.5 mb-5 flex-1">
              <PlanFeature>Unlimited custom panels</PlanFeature>
              <PlanFeature>Full workflow automation</PlanFeature>
              <PlanFeature>Smart process management (MATCH + UPDATE)</PlanFeature>
              <PlanFeature>Cross-panel relation linking</PlanFeature>
              <PlanFeature>Per-record PDF download</PlanFeature>
              <PlanFeature>Field visibility &amp; auto-managed fields</PlanFeature>
              <PlanFeature>Advanced flexibility &amp; data modes</PlanFeature>
              <PlanFeature>Quotation management</PlanFeature>
              <PlanFeature>Priority support</PlanFeature>
            </ul>
            <p className="text-xs text-gray-400 mb-4 italic">Save time, reduce manual work, and scale faster</p>
            <Link href="/register" className="block w-full text-center py-2.5 bg-orange-500 text-white rounded-xl text-sm font-semibold hover:bg-orange-600 transition" data-testid="pro-cta">
              Get Pro
            </Link>
          </div>

          {/* Enterprise */}
          <div className="bg-white rounded-2xl border border-gray-200 p-7 flex flex-col" data-testid="plan-enterprise">
            <div className="mb-5">
              <div className="inline-flex items-center justify-center w-10 h-10 bg-purple-50 rounded-xl mb-3">
                <Crown className="h-5 w-5 text-purple-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Enterprise</h2>
              <p className="text-sm text-gray-400 mt-1">Large-scale or custom needs</p>
            </div>
            <div className="mb-6">
              <span className="text-3xl font-bold text-gray-900">Custom</span>
              <span className="text-gray-400 text-sm"> Pricing</span>
            </div>
            <p className="text-xs text-gray-500 font-medium mb-2">Everything in Pro, plus:</p>
            <ul className="space-y-2.5 mb-8 flex-1">
              <PlanFeature>Custom workflows &amp; automation</PlanFeature>
              <PlanFeature>Dedicated account support</PlanFeature>
              <PlanFeature>API / ERP integrations</PlanFeature>
              <PlanFeature>High-scale system support</PlanFeature>
              <PlanFeature>White-label options</PlanFeature>
              <PlanFeature>Custom reporting</PlanFeature>
            </ul>
            <p className="text-xs text-gray-400 mb-4 italic">Designed for growing and large businesses</p>
            <Link href="/contact" className="block w-full text-center py-2.5 border-2 border-purple-500 text-purple-600 rounded-xl text-sm font-semibold hover:bg-purple-50 transition" data-testid="enterprise-cta">
              Contact Sales
            </Link>
          </div>
        </div>
      </section>

      {/* Why Choose */}
      <section className="bg-slate-50 border-y border-slate-200 py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">Why Choose UdyogConnect?</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <WhyCard icon={<Layers className="h-5 w-5 text-blue-600" />} title="Replace Multiple Tools" desc="One system for inventory, invoices, employees, QC, and more." />
            <WhyCard icon={<Settings className="h-5 w-5 text-orange-500" />} title="Automate Operations" desc="Set up rules once. Let the system handle daily repetitive work." />
            <WhyCard icon={<BarChart3 className="h-5 w-5 text-emerald-600" />} title="Single Dashboard" desc="Manage everything from one place. No switching between apps." />
            <WhyCard icon={<Users className="h-5 w-5 text-purple-600" />} title="Built for India" desc="Designed for Indian business workflows and operations." />
            <WhyCard icon={<Boxes className="h-5 w-5 text-rose-500" />} title="Scalable" desc="Start small with basic features. Scale up as your business grows." />
            <WhyCard icon={<FileText className="h-5 w-5 text-cyan-600" />} title="Custom Panels" desc="Create any data structure your business needs. No coding required." />
          </div>
        </div>
      </section>

      {/* Founding Member Offer */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16" data-testid="founding-offer">
        <div className="bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-2xl p-8 sm:p-10 text-center">
          <div className="inline-flex items-center gap-2 bg-orange-100 text-orange-700 text-xs font-bold px-3 py-1 rounded-full mb-4">
            <Clock className="h-3.5 w-3.5" /> LIMITED TIME
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Founding Member Offer</h2>
          <p className="text-gray-600 mb-6 max-w-lg mx-auto">
            First 500 businesses get <span className="font-bold text-orange-600">50% discount</span> on all plans, priority onboarding, and early access to new features.
          </p>
          <p className="text-sm text-gray-400 mb-6">Once slots are filled, regular pricing will apply.</p>
          <Link href="/register" className="inline-flex items-center gap-2 bg-orange-500 text-white px-6 py-3 rounded-xl font-semibold hover:bg-orange-600 transition" data-testid="founding-cta">
            Claim Your Spot <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">Frequently Asked Questions</h2>
        <div className="space-y-4">
          <FaqItem q="Can I upgrade my plan later?" a="Yes, you can upgrade anytime as your business grows. Your data and settings are preserved." />
          <FaqItem q="Is there any setup cost?" a="No. There are no hidden charges. The price you see is the price you pay." />
          <FaqItem q="Do I need technical knowledge?" a="No. The system is designed for easy use. If you can use WhatsApp, you can use UdyogConnect." />
          <FaqItem q="Is support available?" a="Yes. Onboarding guidance and ongoing support are provided with all paid plans." />
          <FaqItem q="What payment methods do you accept?" a="We accept UPI, credit/debit cards, and net banking." />
          <FaqItem q="Can I cancel anytime?" a="Yes. You can cancel at any time. Your data remains accessible until the end of your billing period." />
        </div>
      </section>
    </div>
  );
}

function PlanFeature({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2">
      <Check className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
      <span className="text-sm text-gray-600">{children}</span>
    </li>
  );
}

function PlanLimit({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <X className="h-4 w-4 text-gray-300 mt-0.5 flex-shrink-0" />
      <span className="text-sm text-gray-400">{children}</span>
    </div>
  );
}

function WhyCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="bg-white p-5 rounded-xl border border-gray-100">
      <div className="mb-2">{icon}</div>
      <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
      <p className="text-xs text-gray-500">{desc}</p>
    </div>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  return (
    <details className="group bg-white border border-gray-200 rounded-xl overflow-hidden" data-testid={`faq-${q.slice(0,20).replace(/\s/g,'-').toLowerCase()}`}>
      <summary className="flex items-center justify-between p-5 cursor-pointer list-none">
        <span className="font-medium text-gray-900 text-sm">{q}</span>
        <ChevronDown className="h-4 w-4 text-gray-400 group-open:rotate-180 transition-transform" />
      </summary>
      <div className="px-5 pb-5 text-sm text-gray-500">{a}</div>
    </details>
  );
}
