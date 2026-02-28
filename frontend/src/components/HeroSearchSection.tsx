'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import EnterpriseSearchBar from './EnterpriseSearchBar';

export default function HeroSearchSection() {
  return (
    <section className="relative min-h-[600px] sm:min-h-[650px] md:min-h-[700px] lg:min-h-[750px] overflow-hidden">
      {/* Full Background Image - No cutting */}
      <div className="absolute inset-0">
        <Image
          src="https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/p7nlljni_image.png"
          alt="Industrial Equipment - Motors, Bearings, Pumps, Valves, Safety Equipment"
          fill
          className="object-cover"
          priority
          sizes="100vw"
          style={{ objectPosition: 'center center' }}
        />
        {/* Light overlay for text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-white/90 via-white/70 to-transparent" />
      </div>
      
      {/* Content - Positioned on top of image */}
      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 sm:pt-12 md:pt-16 text-center">
        
        {/* Logo in hero - UdyogConnect logo + Brand name */}
        <div className="flex items-center justify-center gap-3 mb-6">
          <img 
            src="https://customer-assets.emergentagent.com/job_59d69e96-5add-42b9-88de-4fe2b67c84c6/artifacts/o4stdhdf_image.png"
            alt="UdyogConnect"
            className="h-[70px] w-[70px] sm:h-[77px] sm:w-[77px] object-contain flex-shrink-0"
          />
          <span className="text-2xl sm:text-3xl font-bold tracking-tight">
            <span style={{ color: '#1e4785' }}>Udyog</span>
            <span style={{ color: '#f58220' }}>Connect</span>
          </span>
        </div>
        
        {/* Main Headline */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-4 leading-tight drop-shadow-sm">
          <span style={{ color: '#1e4785' }}>India&apos;s Trusted</span>{' '}
          <span style={{ color: '#f58220' }}>B2B Marketplace</span>
        </h1>
        
        {/* Description */}
        <p className="text-base sm:text-lg md:text-xl text-gray-700 mb-8 max-w-3xl mx-auto leading-relaxed">
          Source motors, bearings, pumps, valves, safety items, and small machinery
          from verified manufacturers, dealers & distributors across India
        </p>
        
        {/* Search Bar - Glass effect card with high z-index for dropdowns */}
        <div className="relative z-50 max-w-3xl mx-auto mb-6 bg-white/80 backdrop-blur-md rounded-2xl p-4 shadow-xl border border-white/50">
          <EnterpriseSearchBar 
            variant="hero" 
            showLocationFilter={true}
          />
        </div>
        
        {/* CTA Buttons - Lower z-index than search */}
        <div className="relative z-10 flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/products"
            className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-blue-600 text-white rounded-full font-semibold hover:bg-blue-700 transition shadow-lg shadow-blue-600/30"
          >
            Browse Products
          </Link>
          <Link
            href="/sell"
            className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-white/90 backdrop-blur-sm text-gray-800 rounded-full font-semibold hover:bg-white transition border border-gray-200 shadow-lg"
          >
            Start Selling <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
        
        {/* Trust badges - Lower z-index than search */}
        <div className="relative z-10 mt-8 flex flex-wrap justify-center gap-6 text-sm text-gray-700">
          <div className="flex items-center gap-2 bg-white/70 backdrop-blur-sm px-4 py-2 rounded-full shadow-md">
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">Verified Sellers</span>
          </div>
          <div className="flex items-center gap-2 bg-white/70 backdrop-blur-sm px-4 py-2 rounded-full shadow-md">
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">Pan India Delivery</span>
          </div>
          <div className="flex items-center gap-2 bg-white/70 backdrop-blur-sm px-4 py-2 rounded-full shadow-md">
            <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span className="font-medium">Bulk Pricing</span>
          </div>
        </div>
      </div>
    </section>
  );
}
