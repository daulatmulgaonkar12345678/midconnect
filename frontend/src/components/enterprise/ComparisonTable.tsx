'use client';

import { X, Send, BadgeCheck } from 'lucide-react';
import type { EnterpriseProductSeller } from '@/lib/api';

interface ComparisonTableProps {
  sellers: EnterpriseProductSeller[];
  onRemove: (sellerId: string) => void;
  onInquiry: (seller: EnterpriseProductSeller) => void;
  onClose: () => void;
}

export default function ComparisonTable({ 
  sellers, 
  onRemove, 
  onInquiry, 
  onClose 
}: ComparisonTableProps) {
  if (sellers.length === 0) return null;

  const formatPrice = (price?: number) => {
    if (!price) return '-';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(price);
  };

  // Collect all unique spec keys from all sellers
  const allSpecKeys = new Set<string>();
  sellers.forEach(seller => {
    Object.keys(seller.searchableAttributes || {}).forEach(key => allSpecKeys.add(key));
  });
  const specKeys = Array.from(allSpecKeys);

  // Get label for a spec key from any seller that has it
  const getSpecLabel = (key: string): string => {
    for (const seller of sellers) {
      if (seller.attributeLabels?.[key]) {
        return seller.attributeLabels[key];
      }
    }
    return key.replace(/_/g, ' ');
  };

  return (
    <div 
      className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-2xl z-50 max-h-[60vh] overflow-auto"
      data-testid="comparison-table"
    >
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Compare Sellers ({sellers.length}/3)</h3>
          <p className="text-xs text-gray-500">Side-by-side comparison of selected suppliers</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          aria-label="Close comparison"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Comparison Grid */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px]">
          <thead>
            <tr className="bg-gray-50">
              <th className="text-left px-4 py-3 text-sm font-semibold text-gray-700 w-40 sticky left-0 bg-gray-50">
                Specification
              </th>
              {sellers.map(seller => (
                <th key={seller.listingId} className="px-4 py-3 text-center min-w-[200px]">
                  <div className="flex flex-col items-center gap-1">
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-gray-900 text-sm">
                        {seller.companyName}
                      </span>
                      <BadgeCheck className="h-4 w-4 text-blue-500" />
                    </div>
                    <span className="text-xs text-gray-500">{seller.location}</span>
                    <button
                      onClick={() => onRemove(seller.listingId)}
                      className="mt-1 text-xs text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {/* Price Row */}
            <tr className="bg-green-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-700 sticky left-0 bg-green-50">
                Price
              </td>
              {sellers.map(seller => (
                <td key={seller.listingId} className="px-4 py-3 text-center">
                  <span className="font-bold text-green-700 text-lg">
                    {formatPrice(seller.lowestPrice)}
                  </span>
                  <span className="text-xs text-gray-500 block">/unit</span>
                </td>
              ))}
            </tr>

            {/* MOQ Row */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-700 sticky left-0 bg-white">
                MOQ
              </td>
              {sellers.map(seller => (
                <td key={seller.listingId} className="px-4 py-3 text-center text-sm text-gray-900">
                  {seller.moq} units
                </td>
              ))}
            </tr>

            {/* Stock Row */}
            <tr className="bg-gray-50">
              <td className="px-4 py-3 text-sm font-medium text-gray-700 sticky left-0 bg-gray-50">
                Stock
              </td>
              {sellers.map(seller => (
                <td key={seller.listingId} className="px-4 py-3 text-center text-sm">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                    seller.stockStatus === 'in_stock' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {seller.stock > 0 ? `${seller.stock} units` : 'Contact'}
                  </span>
                </td>
              ))}
            </tr>

            {/* Lead Time Row */}
            <tr>
              <td className="px-4 py-3 text-sm font-medium text-gray-700 sticky left-0 bg-white">
                Lead Time
              </td>
              {sellers.map(seller => (
                <td key={seller.listingId} className="px-4 py-3 text-center text-sm text-gray-900">
                  {seller.leadTimeDays ? `${seller.leadTimeDays} days` : '-'}
                </td>
              ))}
            </tr>

            {/* Spec Rows */}
            {specKeys.map((key, idx) => (
              <tr key={key} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                <td className={`px-4 py-3 text-sm font-medium text-gray-700 sticky left-0 ${idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}`}>
                  {getSpecLabel(key)}
                </td>
                {sellers.map(seller => (
                  <td key={seller.listingId} className="px-4 py-3 text-center text-sm text-gray-900">
                    {seller.searchableAttributes?.[key] !== undefined 
                      ? String(seller.searchableAttributes[key])
                      : '-'
                    }
                  </td>
                ))}
              </tr>
            ))}

            {/* Action Row */}
            <tr className="bg-white border-t-2 border-gray-200">
              <td className="px-4 py-4 sticky left-0 bg-white">
                <span className="text-sm font-semibold text-gray-700">Action</span>
              </td>
              {sellers.map(seller => (
                <td key={seller.listingId} className="px-4 py-4 text-center">
                  <button
                    onClick={() => onInquiry(seller)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm transition-colors"
                    data-testid={`compare-rfq-${seller.listingId}`}
                  >
                    <Send className="h-4 w-4" />
                    Request Quote
                  </button>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
