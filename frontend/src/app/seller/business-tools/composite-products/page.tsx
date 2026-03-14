'use client';

import { usePermissions } from '../layout';
import { Layers, Construction } from 'lucide-react';

export default function CompositeProductsPage() {
  const { hasPermission } = usePermissions();

  if (!hasPermission('manage_listings')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <Layers className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to manage composite products.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Composite Products</h1>
        <p className="text-gray-600 mt-1">Bundle products into kits</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
        <Construction className="h-16 w-16 text-pink-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Coming Soon</h2>
        <p className="text-gray-600 max-w-md mx-auto">
          Create composite products by bundling multiple base products together.
          Stock will automatically adjust when composite products are sold.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <span className="px-3 py-1 bg-pink-50 text-pink-600 rounded-full text-sm">
            Bundle products
          </span>
          <span className="px-3 py-1 bg-pink-50 text-pink-600 rounded-full text-sm">
            Auto inventory sync
          </span>
          <span className="px-3 py-1 bg-pink-50 text-pink-600 rounded-full text-sm">
            Kit pricing
          </span>
        </div>
      </div>
    </div>
  );
}
