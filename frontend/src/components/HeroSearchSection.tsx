'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import EnterpriseSearchBar from './EnterpriseSearchBar';

export default function HeroSearchSection() {
  return (
    <section className="bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-20">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
            India's Trusted B2B Marketplace
          </h1>
          <p className="text-lg md:text-xl text-blue-100 mb-8">
            Connect directly with verified manufacturers, dealers, and distributors
          </p>
          
          {/* Enterprise Search Bar */}
          <div className="max-w-3xl mx-auto mb-8">
            <EnterpriseSearchBar 
              variant="hero" 
              showLocationFilter={true}
            />
          </div>
          
          {/* Popular Searches */}
          <div className="flex flex-wrap justify-center gap-2 mb-8">
            <span className="text-blue-200 text-sm">Popular:</span>
            {['Motors', 'Pumps', 'Transformers', 'Cables', 'Switches'].map((term) => (
              <Link
                key={term}
                href={`/products?q=${encodeURIComponent(term.toLowerCase())}`}
                className="px-3 py-1 bg-white/10 hover:bg-white/20 rounded-full text-sm transition"
              >
                {term}
              </Link>
            ))}
          </div>
          
          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/products"
              className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition flex items-center justify-center gap-2"
            >
              Browse Products <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/sell"
              className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white/10 transition text-center"
            >
              Start Selling
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
