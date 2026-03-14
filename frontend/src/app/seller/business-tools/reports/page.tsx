'use client';

import { usePermissions } from '../layout';
import { BarChart3, Construction } from 'lucide-react';

export default function ReportsPage() {
  const { hasPermission } = usePermissions();

  if (!hasPermission('view_reports')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to view reports.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600 mt-1">Sales analytics and insights</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
        <Construction className="h-16 w-16 text-cyan-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Coming Soon</h2>
        <p className="text-gray-600 max-w-md mx-auto">
          View comprehensive reports on sales, inventory, and buyer activity.
          Filter by date range, product, or category.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <span className="px-3 py-1 bg-cyan-50 text-cyan-600 rounded-full text-sm">
            Monthly sales
          </span>
          <span className="px-3 py-1 bg-cyan-50 text-cyan-600 rounded-full text-sm">
            Top products
          </span>
          <span className="px-3 py-1 bg-cyan-50 text-cyan-600 rounded-full text-sm">
            Inventory status
          </span>
          <span className="px-3 py-1 bg-cyan-50 text-cyan-600 rounded-full text-sm">
            Buyer analytics
          </span>
        </div>
      </div>
    </div>
  );
}
