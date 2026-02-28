'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import EnterpriseSearchBar from './EnterpriseSearchBar';

export default function HeroSearchSection() {
  return (
    <section className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white overflow-hidden">
      {/* Background Image - Positioned at bottom right */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Desktop: Image on right side */}
        <div className="hidden md:block absolute right-0 bottom-0 w-[55%] h-full">
          <Image
            src="https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/ge1uhf1k_image.png"
            alt="Industrial Equipment - B2B Marketplace"
            fill
            className="object-cover object-left-bottom opacity-90"
            priority
            sizes="(max-width: 768px) 100vw, 55vw"
          />
          {/* Gradient overlay for text readability */}
          <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-blue-700/80 to-transparent" />
        </div>
        
        {/* Mobile: Subtle background image */}
        <div className="md:hidden absolute inset-0">
          <Image
            src="https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/ge1uhf1k_image.png"
            alt="Industrial Equipment"
            fill
            className="object-cover object-center opacity-20"
            priority
            sizes="100vw"
          />
        </div>
      </div>
      
      {/* Content Container */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16 lg:py-20">
        <div className="grid md:grid-cols-2 gap-8 items-center">
          {/* Left Content - Text & Search */}
          <div className="text-center md:text-left">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl xl:text-6xl font-bold mb-4 leading-tight">
              India&apos;s Trusted
              <span className="block text-yellow-300">B2B Marketplace</span>
            </h1>
            <p className="text-base sm:text-lg lg:text-xl text-blue-100 mb-6 max-w-lg mx-auto md:mx-0">
              Source industrial equipment directly from verified manufacturers, dealers & distributors across India
            </p>
            
            {/* Enterprise Search Bar */}
            <div className="max-w-xl mx-auto md:mx-0 mb-6">
              <EnterpriseSearchBar 
                variant="hero" 
                showLocationFilter={true}
              />
            </div>
            
            {/* Popular Searches */}
            <div className="flex flex-wrap justify-center md:justify-start gap-2 mb-6">
              <span className="text-blue-200 text-sm">Popular:</span>
              {['Motors', 'Pumps', 'Bearings', 'Valves', 'Tools'].map((term) => (
                <Link
                  key={term}
                  href={`/products?q=${encodeURIComponent(term.toLowerCase())}`}
                  className="px-3 py-1 bg-white/15 hover:bg-white/25 rounded-full text-sm transition backdrop-blur-sm"
                >
                  {term}
                </Link>
              ))}
            </div>
            
            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center md:justify-start">
              <Link
                href="/products"
                className="bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold hover:bg-blue-50 transition flex items-center justify-center gap-2 shadow-lg"
              >
                Browse Products <ArrowRight className="h-5 w-5" />
              </Link>
              <Link
                href="/sell"
                className="border-2 border-white text-white px-6 py-3 rounded-lg font-semibold hover:bg-white/10 transition text-center"
              >
                Start Selling
              </Link>
            </div>
            
            {/* Trust Indicators - Mobile visible */}
            <div className="mt-8 flex flex-wrap justify-center md:justify-start gap-4 text-sm text-blue-100">
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Verified Sellers
              </div>
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Pan India Delivery
              </div>
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Bulk Pricing
              </div>
            </div>
          </div>
          
          {/* Right Side - Empty space for image (handled by absolute positioning) */}
          <div className="hidden md:block" aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}
