import { Metadata } from 'next';
import Link from 'next/link';
import { Store, Camera, Tag, MessageCircle, BarChart, CheckCircle, ArrowRight } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Seller Guide - MidConnect',
  description: 'Complete guide for sellers on MidConnect. Learn how to list products, manage orders, and grow your business.',
};

export default function SellerGuidePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Seller Guide</h1>
        <p className="text-xl text-gray-600">
          Everything you need to know to succeed as a seller on MidConnect
        </p>
      </div>

      {/* Getting Started */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Store className="h-6 w-6 text-blue-600" />
          Getting Started
        </h2>
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">1</div>
            <div>
              <h3 className="font-semibold text-gray-900">Create Your Account</h3>
              <p className="text-gray-600">Sign up with your business email and verify your account.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">2</div>
            <div>
              <h3 className="font-semibold text-gray-900">Complete Your Profile</h3>
              <p className="text-gray-600">Add your business name, address, and contact details.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">3</div>
            <div>
              <h3 className="font-semibold text-gray-900">Verify GST</h3>
              <p className="text-gray-600">Upload your GST certificate to get the verified seller badge.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">4</div>
            <div>
              <h3 className="font-semibold text-gray-900">List Your Products</h3>
              <p className="text-gray-600">Add your products with photos, specifications, and pricing.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Creating Listings */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Camera className="h-6 w-6 text-blue-600" />
          Creating Great Listings
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-green-50 rounded-xl p-6">
            <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
              <CheckCircle className="h-5 w-5" /> Do's
            </h3>
            <ul className="space-y-2 text-green-700 text-sm">
              <li>• Use high-quality product images</li>
              <li>• Write detailed, accurate descriptions</li>
              <li>• Include all technical specifications</li>
              <li>• Set competitive pricing</li>
              <li>• Update stock availability regularly</li>
              <li>• Respond to enquiries within 24 hours</li>
            </ul>
          </div>
          <div className="bg-red-50 rounded-xl p-6">
            <h3 className="font-semibold text-red-800 mb-3">Don'ts</h3>
            <ul className="space-y-2 text-red-700 text-sm">
              <li>• Use stock photos from internet</li>
              <li>• Write vague or misleading descriptions</li>
              <li>• Hide pricing or important details</li>
              <li>• Ignore buyer enquiries</li>
              <li>• List products you can't supply</li>
              <li>• Use inappropriate content</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Pricing Strategy */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Tag className="h-6 w-6 text-blue-600" />
          Pricing Strategy
        </h2>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-600 mb-4">
            MidConnect allows you to set quantity-based pricing slabs to offer better deals for bulk orders.
          </p>
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-3">Example Pricing Slabs:</h4>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Quantity</th>
                  <th className="text-right py-2">Price per Unit</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-2">1-10 units</td>
                  <td className="text-right">₹1,000</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2">11-50 units</td>
                  <td className="text-right">₹950 (-5%)</td>
                </tr>
                <tr>
                  <td className="py-2">50+ units</td>
                  <td className="text-right">₹900 (-10%)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Managing Enquiries */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <MessageCircle className="h-6 w-6 text-blue-600" />
          Managing Enquiries
        </h2>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <ul className="space-y-4">
            <li className="flex items-start gap-3">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded text-xs font-medium">Tip 1</span>
              <p className="text-gray-600">Respond to enquiries within 24 hours for better conversion.</p>
            </li>
            <li className="flex items-start gap-3">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded text-xs font-medium">Tip 2</span>
              <p className="text-gray-600">Provide detailed quotes with GST breakdown and delivery timeline.</p>
            </li>
            <li className="flex items-start gap-3">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded text-xs font-medium">Tip 3</span>
              <p className="text-gray-600">Be professional and courteous in all communications.</p>
            </li>
            <li className="flex items-start gap-3">
              <span className="bg-blue-100 text-blue-600 px-2 py-1 rounded text-xs font-medium">Tip 4</span>
              <p className="text-gray-600">Follow up with buyers who haven't responded.</p>
            </li>
          </ul>
        </div>
      </section>

      {/* Analytics */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <BarChart className="h-6 w-6 text-blue-600" />
          Track Your Performance
        </h2>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-600 mb-4">
            Use the seller dashboard to track key metrics and improve your performance:
          </p>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">Views</p>
              <p className="text-gray-600 text-sm">How many see your listings</p>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-green-600">Enquiries</p>
              <p className="text-gray-600 text-sm">Interest from buyers</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-purple-600">Conversion</p>
              <p className="text-gray-600 text-sm">Enquiries to orders</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <div className="bg-blue-600 rounded-xl p-8 text-center text-white">
        <h2 className="text-2xl font-bold mb-4">Ready to Start Selling?</h2>
        <p className="mb-6 text-blue-100">
          Join thousands of sellers already growing their business on MidConnect.
        </p>
        <Link 
          href="/sell" 
          className="inline-flex items-center gap-2 bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold hover:bg-blue-50 transition"
        >
          Become a Seller <ArrowRight className="h-5 w-5" />
        </Link>
      </div>
    </div>
  );
}
