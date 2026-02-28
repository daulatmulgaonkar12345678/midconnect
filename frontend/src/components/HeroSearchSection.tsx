'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import EnterpriseSearchBar from './EnterpriseSearchBar';

export default function HeroSearchSection() {
  return (
    <section className="relative overflow-hidden">
      {/* Background - Light blue gradient with industrial cityscape feel */}
      <div className="absolute inset-0 bg-gradient-to-b from-blue-50 via-blue-100/50 to-blue-200/30" />
      
      {/* Background pattern overlay for depth */}
      <div className="absolute inset-0 opacity-30" style={{
        backgroundImage: `radial-gradient(circle at 25% 25%, rgba(59, 130, 246, 0.1) 0%, transparent 50%),
                          radial-gradient(circle at 75% 75%, rgba(59, 130, 246, 0.1) 0%, transparent 50%)`
      }} />
      
      {/* Content Container */}
      <div className="relative z-10">
        {/* Top Section - Centered Content */}
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-4 md:pt-12 md:pb-6 text-center">
          
          {/* Logo in hero - matching reference */}
          <div className="flex items-center justify-center gap-2 mb-6">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
            </div>
            <span className="text-2xl font-bold text-blue-600">Udyog Connect</span>
          </div>
          
          {/* Main Headline */}
          <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 mb-4 leading-tight">
            India&apos;s Trusted B2B Marketplace
          </h1>
          
          {/* Description */}
          <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed">
            Source motors, bearings, pumps, valves, safety items, and small machinery
            from verified manufacturers, dealers & distributors across India
          </p>
          
          {/* Enterprise Search Bar */}
          <div className="max-w-3xl mx-auto mb-6">
            <EnterpriseSearchBar 
              variant="hero" 
              showLocationFilter={true}
            />
          </div>
          
          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-4">
            <Link
              href="/products"
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-blue-600 text-white rounded-full font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-600/25"
            >
              Browse Products
            </Link>
            <Link
              href="/sell"
              className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white text-gray-800 rounded-full font-semibold hover:bg-gray-50 transition border border-gray-200 shadow-lg"
            >
              Start Selling <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
        
        {/* Bottom Section - Industrial Equipment Image (Full Width) */}
        <div className="relative w-full h-[180px] sm:h-[250px] md:h-[320px] lg:h-[380px] mt-2">
          {/* The image container spans full viewport width */}
          <div className="absolute inset-0 overflow-hidden">
            <Image
              src="https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/p7nlljni_image.png"
              alt="Industrial Equipment - Motors, Bearings, Pumps, Valves, Safety Equipment"
              fill
              className="object-cover object-top scale-110"
              priority
              sizes="100vw"
              style={{ objectPosition: 'center top' }}
            />
          </div>
          {/* Gradient fade at top to blend with content */}
          <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-blue-100 via-blue-100/60 to-transparent pointer-events-none z-10" />
        </div>
      </div>
    </section>
  );
}
