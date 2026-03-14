'use client';

import { usePermissions } from '../layout';
import { FileText, Construction } from 'lucide-react';

export default function InvoicesPage() {
  const { hasPermission } = usePermissions();

  if (!hasPermission('create_invoice')) {
    return (
      <div className="text-center py-12 bg-white rounded-xl shadow-sm border">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Access Denied</h3>
        <p className="text-gray-500 mt-1">You don&apos;t have permission to create invoices.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
        <p className="text-gray-600 mt-1">Create and manage invoices</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
        <Construction className="h-16 w-16 text-orange-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Coming Soon</h2>
        <p className="text-gray-600 max-w-md mx-auto">
          The invoice system is being built. You&apos;ll be able to create invoices,
          generate PDFs, and track payments.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <span className="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-sm">
            Auto-generated invoice numbers
          </span>
          <span className="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-sm">
            PDF generation
          </span>
          <span className="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-sm">
            Inventory auto-deduction
          </span>
        </div>
      </div>
    </div>
  );
}
