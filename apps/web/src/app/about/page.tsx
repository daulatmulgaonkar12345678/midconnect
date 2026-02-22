import { Metadata } from 'next';
import Link from 'next/link';
import { Building, Users, Target, Award } from 'lucide-react';

export const metadata: Metadata = {
  title: 'About Us - MidConnect',
  description: "Learn about India's trusted B2B marketplace for industrial products. Our mission, values, and commitment to connecting buyers and sellers.",
};

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">About MidConnect</h1>
        <p className="text-xl text-gray-600">
          India's trusted marketplace for industrial products and B2B commerce
        </p>
      </div>

      <div className="prose prose-lg max-w-none">
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="h-6 w-6 text-blue-600" />
            Our Mission
          </h2>
          <p className="text-gray-600">
            We are building India's most trusted B2B marketplace, connecting manufacturers, 
            dealers, and distributors with verified buyers across the country. Our platform 
            simplifies industrial procurement by providing transparent pricing, verified sellers, 
            and seamless communication.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Building className="h-6 w-6 text-blue-600" />
            What We Do
          </h2>
          <ul className="space-y-3 text-gray-600">
            <li>Connect verified industrial sellers with serious buyers</li>
            <li>Provide transparent pricing with quantity-based discounts</li>
            <li>Enable GST-compliant business transactions</li>
            <li>Offer pan-India delivery network</li>
            <li>Secure communication between buyers and sellers</li>
          </ul>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Award className="h-6 w-6 text-blue-600" />
            Why Choose Us
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-blue-50 p-6 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">GST Verified Sellers</h3>
              <p className="text-gray-600 text-sm">All sellers undergo GST verification for trust and compliance.</p>
            </div>
            <div className="bg-green-50 p-6 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Quality Assurance</h3>
              <p className="text-gray-600 text-sm">Products meet industry standards with proper specifications.</p>
            </div>
            <div className="bg-purple-50 p-6 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Competitive Pricing</h3>
              <p className="text-gray-600 text-sm">Compare prices from multiple sellers to get the best deals.</p>
            </div>
            <div className="bg-orange-50 p-6 rounded-lg">
              <h3 className="font-semibold text-gray-900 mb-2">Pan India Reach</h3>
              <p className="text-gray-600 text-sm">Sellers across India delivering to your location.</p>
            </div>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Users className="h-6 w-6 text-blue-600" />
            Join Our Community
          </h2>
          <p className="text-gray-600 mb-6">
            Whether you're a buyer looking for quality industrial products or a seller 
            wanting to reach more customers, MidConnect is the platform for you.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link 
              href="/register" 
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
            >
              Create Account
            </Link>
            <Link 
              href="/sell" 
              className="border border-blue-600 text-blue-600 px-6 py-3 rounded-lg hover:bg-blue-50 transition"
            >
              Start Selling
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
