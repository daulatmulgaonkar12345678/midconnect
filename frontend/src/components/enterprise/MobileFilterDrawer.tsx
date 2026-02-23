'use client';

import { useEffect } from 'react';
import { X, Filter } from 'lucide-react';
import FilterPanel from './FilterPanel';

interface Facet {
  values: (string | number)[];
  count: number;
  metadata: {
    label: string;
    fieldType: string;
    unit?: string;
    filterable?: boolean;
    options?: string[];
  };
}

interface MobileFilterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  facets: Record<string, Facet>;
  activeFilters: Record<string, unknown>;
  onFilterChange: (filters: Record<string, unknown>) => void;
  onClearFilters: () => void;
  isLoading?: boolean;
  resultCount: number;
}

export default function MobileFilterDrawer({
  isOpen,
  onClose,
  facets,
  activeFilters,
  onFilterChange,
  onClearFilters,
  isLoading,
  resultCount
}: MobileFilterDrawerProps) {
  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const filterCount = Object.keys(activeFilters).length;

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div 
        className={`fixed inset-y-0 left-0 w-[85%] max-w-sm bg-white z-50 transform transition-transform duration-300 ease-in-out lg:hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        data-testid="mobile-filter-drawer"
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-gray-600" />
            <span className="font-semibold text-gray-900">Filters</span>
            {filterCount > 0 && (
              <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full">
                {filterCount}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
            aria-label="Close filters"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Filter Content */}
        <div className="overflow-y-auto h-[calc(100%-120px)] p-4">
          <FilterPanel
            facets={facets}
            activeFilters={activeFilters}
            onFilterChange={onFilterChange}
            onClearFilters={onClearFilters}
            isLoading={isLoading}
          />
        </div>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
          <button
            onClick={onClose}
            className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
          >
            Show {resultCount} Results
          </button>
        </div>
      </div>
    </>
  );
}
