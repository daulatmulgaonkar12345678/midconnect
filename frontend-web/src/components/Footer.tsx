import Link from 'next/link';
import { ShoppingBag } from 'lucide-react';
import { APP_NAME, FOOTER } from '@/lib/config';

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <ShoppingBag className="h-8 w-8 text-blue-400" />
              <span className="text-xl font-bold">{APP_NAME}</span>
            </div>
            <p className="text-gray-400 text-sm">
              {FOOTER.tagline}
            </p>
          </div>

          {/* Categories */}
          <div>
            <h3 className="font-semibold mb-4">Categories</h3>
            <ul className="space-y-2 text-gray-400 text-sm">
              <li><Link href="/categories" className="hover:text-white">All Categories</Link></li>
              <li><Link href="/products" className="hover:text-white">Browse Products</Link></li>
              <li><Link href="/search" className="hover:text-white">Search Products</Link></li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-2 text-gray-400 text-sm">
              <li><Link href="/about" className="hover:text-white">About Us</Link></li>
              <li><Link href="/contact" className="hover:text-white">Contact</Link></li>
              <li><Link href="/privacy" className="hover:text-white">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-white">Terms of Service</Link></li>
            </ul>
          </div>

          {/* For Sellers */}
          <div>
            <h3 className="font-semibold mb-4">For Sellers</h3>
            <ul className="space-y-2 text-gray-400 text-sm">
              <li><Link href="/sell" className="hover:text-white">Start Selling</Link></li>
              <li><Link href="/seller-guide" className="hover:text-white">Seller Guide</Link></li>
              <li><Link href="/pricing" className="hover:text-white">Pricing Plans</Link></li>
            </ul>
            <div className="mt-4">
              <p className="text-sm text-gray-400 mb-2">Download our app:</p>
              <div className="flex gap-2">
                <span className="bg-gray-800 px-3 py-1 rounded text-xs">Android</span>
                <span className="bg-gray-800 px-3 py-1 rounded text-xs">iOS</span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400 text-sm">
          {FOOTER.copyright(new Date().getFullYear())}
        </div>
      </div>
    </footer>
  );
}
