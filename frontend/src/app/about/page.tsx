import { Metadata } from 'next';
import Link from 'next/link';
import { Target, Layers, Award, Users, ArrowRight, CheckCircle2, Settings, BarChart3, MessageSquare, Boxes, FileText, Zap } from 'lucide-react';

export const metadata: Metadata = {
  title: 'About Us - UdyogConnect',
  description: "India's growing platform for business management and automation. Simplify operations, automate workflows, and manage everything from one system.",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
          About UdyogConnect
        </h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          India's growing platform for business management and automation
        </p>
      </section>

      {/* Mission */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-8 sm:p-10">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
              <Target className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">Our Mission</h2>
              <p className="text-gray-600 text-base leading-relaxed">
                Our mission is to help businesses <span className="font-semibold text-blue-700">run smarter, faster, and more efficiently</span>. We aim to simplify business operations by bringing everything into one system — so you can focus on growing your business, not managing tools.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* What We Do */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-3">What We Do</h2>
          <p className="text-gray-500">UdyogConnect is more than just a marketplace. We provide a <span className="font-medium text-gray-700">complete business management system</span>.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <WhatCard icon={<Boxes className="h-5 w-5 text-blue-600" />} title="Manage Inventory & Stock" desc="Track products, stock levels, and reorder points in real time." />
          <WhatCard icon={<Users className="h-5 w-5 text-purple-600" />} title="Track Employees & Daily Work" desc="Employee management, attendance tracking, and task assignment." />
          <WhatCard icon={<Settings className="h-5 w-5 text-orange-500" />} title="Automate Repetitive Tasks" desc="Set rules once — the system handles updates, record creation, and linking automatically." />
          <WhatCard icon={<MessageSquare className="h-5 w-5 text-green-600" />} title="WhatsApp Communication" desc="Communicate with customers directly via WhatsApp integration." />
          <WhatCard icon={<Layers className="h-5 w-5 text-cyan-600" />} title="Custom Panels" desc="Create any data structure your business needs — QC, dispatch, material tracking, and more." />
          <WhatCard icon={<FileText className="h-5 w-5 text-rose-500" />} title="Invoices & Purchase Orders" desc="Generate invoices, manage purchase orders, quotations, and buyer/supplier records." />
          <WhatCard icon={<Zap className="h-5 w-5 text-amber-500" />} title="Cross-Panel Automation" desc="Link panels together with smart rules. QC results auto-update inventory, invoices trigger workflows." />
          <WhatCard icon={<BarChart3 className="h-5 w-5 text-indigo-600" />} title="PDF & Excel Exports" desc="Download records as PDFs for authority review. Export data to Excel for reporting." />
          <WhatCard icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />} title="Field Visibility Control" desc="Auto-managed fields protect critical data. Control who can see and edit what." />
        </div>
      </section>

      {/* Vision */}
      <section className="bg-slate-50 border-y border-slate-200 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Our Vision</h2>
          <p className="text-gray-600 text-base max-w-2xl mx-auto leading-relaxed mb-3">
            We are building <span className="font-semibold text-gray-800">a single platform to run and automate entire businesses</span>.
          </p>
          <p className="text-gray-400 text-sm max-w-xl mx-auto">
            Our goal is to become the system that businesses rely on daily — just like accounting software, but for full operations.
          </p>
        </div>
      </section>

      {/* Why Choose */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">
          Why Businesses Choose UdyogConnect
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <WhyItem text="Simple and easy to use" />
          <WhyItem text="No technical knowledge required" />
          <WhyItem text="Saves time and reduces manual work" />
          <WhyItem text="Flexible and customizable" />
          <WhyItem text="Grows with your business" />
          <WhyItem text="Built for Indian business workflows" />
        </div>
      </section>

      {/* Who Is It For */}
      <section className="bg-gradient-to-r from-orange-50 to-amber-50 border-y border-orange-100 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Who Is It For?</h2>
          <p className="text-center text-gray-500 mb-8">UdyogConnect is built for:</p>
          <div className="flex flex-wrap justify-center gap-3">
            <AudienceTag>Retail Shop Owners</AudienceTag>
            <AudienceTag>Distributors</AudienceTag>
            <AudienceTag>Manufacturers</AudienceTag>
            <AudienceTag>Service Providers</AudienceTag>
            <AudienceTag>Small &amp; Growing Businesses</AudienceTag>
          </div>
        </div>
      </section>

      {/* Join Us CTA */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">Join Us</h2>
        <p className="text-gray-500 mb-8 max-w-lg mx-auto">
          Whether you want to manage your business better, automate daily work, or grow faster with technology — UdyogConnect is built for you.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link href="/register" className="inline-flex items-center gap-2 bg-blue-600 text-white px-7 py-3 rounded-xl font-semibold hover:bg-blue-700 transition" data-testid="about-create-account">
            Create Account <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/contact" className="inline-flex items-center gap-2 border-2 border-blue-600 text-blue-600 px-7 py-3 rounded-xl font-semibold hover:bg-blue-50 transition" data-testid="about-get-demo">
            Get Demo
          </Link>
        </div>
      </section>
    </div>
  );
}

function WhatCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5 hover:border-gray-200 transition">
      <div className="mb-2.5">{icon}</div>
      <h3 className="font-semibold text-gray-900 text-sm mb-1">{title}</h3>
      <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
    </div>
  );
}

function WhyItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 bg-white border border-gray-100 rounded-xl px-5 py-3.5">
      <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500 flex-shrink-0" />
      <span className="text-sm text-gray-700 font-medium">{text}</span>
    </div>
  );
}

function AudienceTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="bg-white border border-orange-200 text-gray-700 text-sm font-medium px-4 py-2 rounded-full">
      {children}
    </span>
  );
}
