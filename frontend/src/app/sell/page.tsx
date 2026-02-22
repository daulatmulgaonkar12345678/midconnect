'use client';

import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { Store, CheckCircle, ArrowRight, BadgeCheck, TrendingUp, Users } from 'lucide-react';

export default function SellPage() {
  const { isAuthenticated, isSeller, loading } = useAuth();

  // Already a seller - redirect to dashboard
  if (!loading && isAuthenticated && isSeller) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">You're Already a Seller!</h1>
        <p className="text-gray-500 mb-6">Access your seller dashboard to manage listings</p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
        >
          Go to Dashboard <ArrowRight className="h-5 w-5" />
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-green-600 to-green-800 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl">
            <h1 className="text-4xl md:text-5xl font-bold mb-6">
              Start Selling on India's Fastest Growing MidConnect Marketplace
            </h1>
            <p className="text-xl text-green-100 mb-8">
              Reach thousands of verified buyers. List your products, get enquiries, and grow your business.
            </p>
            {!loading && (
              isAuthenticated ? (
                <Link
                  href="/become-seller"
                  className="inline-flex items-center gap-2 bg-white text-green-600 px-8 py-4 rounded-lg font-semibold hover:bg-green-50 transition"
                >
                  <Store className="h-5 w-5" /> Become a Seller
                </Link>
              ) : (
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link
                    href="/register"
                    className="inline-flex items-center justify-center gap-2 bg-white text-green-600 px-8 py-4 rounded-lg font-semibold hover:bg-green-50 transition"
                  >
                    Create Account
                  </Link>
                  <Link
                    href="/login?redirect=/sell"
                    className="inline-flex items-center justify-center gap-2 border-2 border-white text-white px-8 py-4 rounded-lg font-semibold hover:bg-white/10 transition"
                  >
                    Already have account? Login
                  </Link>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">Why Sell on MidConnect?</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Reach More Buyers</h3>
              <p className="text-gray-500">
                Connect with thousands of verified industrial buyers across India looking for quality products.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <BadgeCheck className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">GST Verified Trust</h3>
              <p className="text-gray-500">
                Get verified seller badge to build trust. Buyers prefer GST-verified sellers for business transactions.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-8 w-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Grow Your Business</h3>
              <p className="text-gray-500">
                Get direct enquiries, negotiate deals, and expand your customer base without middlemen.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: 1, title: 'Create Account', desc: 'Sign up with your business details' },
              { step: 2, title: 'Verify GST', desc: 'Submit GST for verification badge' },
              { step: 3, title: 'List Products', desc: 'Add your products with pricing' },
              { step: 4, title: 'Get Enquiries', desc: 'Receive and convert buyer leads' },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                  {item.step}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-gray-500 text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-blue-600">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to Start Selling?</h2>
          <p className="text-blue-100 mb-8">
            Join thousands of sellers who are growing their business on MidConnect
          </p>
          {!loading && (
            isAuthenticated ? (
              <Link
                href="/become-seller"
                className="inline-flex items-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold hover:bg-blue-50 transition"
              >
                Complete Seller Registration
              </Link>
            ) : (
              <Link
                href="/register"
                className="inline-flex items-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-lg font-semibold hover:bg-blue-50 transition"
              >
                Get Started Free
              </Link>
            )
          )}
        </div>
      </section>
    </div>
  );
}
