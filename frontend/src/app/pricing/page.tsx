import { Metadata } from 'next';
import Link from 'next/link';
import { Check, X, Star, Zap, Shield, Crown } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Pricing - UdyogConnect',
  description: 'Simple, transparent pricing for sellers on UdyogConnect. Start free and grow your business.',
};

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Simple, Transparent Pricing</h1>
        <p className="text-xl text-gray-600">
          Start free and scale as your business grows
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="grid md:grid-cols-3 gap-8 mb-16">
        {/* Free Plan */}
        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-gray-200">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 rounded-full mb-4">
              <Star className="h-6 w-6 text-gray-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Starter</h2>
            <p className="text-gray-500 mt-2">Perfect for getting started</p>
          </div>
          <div className="text-center mb-6">
            <span className="text-4xl font-bold text-gray-900">Free</span>
            <span className="text-gray-500">/forever</span>
          </div>
          <ul className="space-y-3 mb-8">
            <Feature included>Up to 5 product listings</Feature>
            <Feature included>10 enquiries per month</Feature>
            <Feature included>Basic seller profile</Feature>
            <Feature included>Email support</Feature>
            <Feature>Priority search ranking</Feature>
            <Feature>Featured listings</Feature>
            <Feature>Analytics dashboard</Feature>
          </ul>
          <Link 
            href="/register" 
            className="block w-full text-center py-3 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition"
          >
            Get Started Free
          </Link>
        </div>

        {/* Pro Plan */}
        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-blue-600 relative">
          <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
            <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium">
              Most Popular
            </span>
          </div>
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-4">
              <Zap className="h-6 w-6 text-blue-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Professional</h2>
            <p className="text-gray-500 mt-2">For growing businesses</p>
          </div>
          <div className="text-center mb-6">
            <span className="text-4xl font-bold text-gray-900">₹999</span>
            <span className="text-gray-500">/month</span>
          </div>
          <ul className="space-y-3 mb-8">
            <Feature included>Unlimited product listings</Feature>
            <Feature included>Unlimited enquiries per month</Feature>
            <Feature included>Verified seller badge</Feature>
            <Feature included>Priority support</Feature>
            <Feature included>Priority search ranking</Feature>
            <Feature included>Basic analytics</Feature>
            <Feature>Featured listings</Feature>
          </ul>
          <Link 
            href="/register" 
            className="block w-full text-center py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Start 21-Day Free Trial
          </Link>
        </div>

        {/* Enterprise Plan */}
        <div className="bg-white rounded-xl shadow-lg p-8 border-2 border-gray-200">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-purple-100 rounded-full mb-4">
              <Crown className="h-6 w-6 text-purple-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Enterprise</h2>
            <p className="text-gray-500 mt-2">For large businesses</p>
          </div>
          <div className="text-center mb-6">
            <span className="text-4xl font-bold text-gray-900">₹4,999</span>
            <span className="text-gray-500">/month</span>
          </div>
          <ul className="space-y-3 mb-8">
            <Feature included>Everything in Professional</Feature>
            <Feature included>Unlimited enquiries</Feature>
            <Feature included>Featured listings (5/month)</Feature>
            <Feature included>Advanced analytics</Feature>
            <Feature included>Dedicated account manager</Feature>
            <Feature included>API access</Feature>
            <Feature included>Custom integrations</Feature>
          </ul>
          <Link 
            href="/contact" 
            className="block w-full text-center py-3 border-2 border-purple-600 text-purple-600 rounded-lg hover:bg-purple-50 transition"
          >
            Contact Sales
          </Link>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="bg-gray-50 rounded-xl p-8">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Frequently Asked Questions</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Can I upgrade or downgrade anytime?</h3>
            <p className="text-gray-600 text-sm">Yes, you can change your plan at any time. Changes take effect immediately.</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">What happens after my trial ends?</h3>
            <p className="text-gray-600 text-sm">You'll be moved to the free plan unless you choose to subscribe.</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">Is there a setup fee?</h3>
            <p className="text-gray-600 text-sm">No, there are no setup fees or hidden charges.</p>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 mb-2">What payment methods do you accept?</h3>
            <p className="text-gray-600 text-sm">We accept UPI, credit/debit cards, and net banking.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Feature({ children, included = false }: { children: React.ReactNode; included?: boolean }) {
  return (
    <li className="flex items-center gap-2">
      {included ? (
        <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
      ) : (
        <X className="h-5 w-5 text-gray-300 flex-shrink-0" />
      )}
      <span className={included ? 'text-gray-700' : 'text-gray-400'}>{children}</span>
    </li>
  );
}
