'use client';

import { useState, useCallback, useEffect } from 'react';
import { Filter, X, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react';

interface FacetMetadata {
  label: string;
  fieldType: string;
  unit?: string;
  filterable?: boolean;
  options?: string[];
}

interface Facet {
  values: (string | number)[];
  count: number;
  metadata: FacetMetadata;
}

interface FilterPanelProps {
  facets: Record<string, Facet>;
  activeFilters: Record<string, unknown>;
  onFilterChange: (filters: Record<string, unknown>) => void;
  onClearFilters: () => void;
  isLoading?: boolean;
}

interface FilterChip {
  key: string;
  label: string;
  value: string;
}

export default function FilterPanel({ 
  facets, 
  activeFilters, 
  onFilterChange, 
  onClearFilters,
  isLoading 
}: FilterPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [localFilters, setLocalFilters] = useState<Record<string, unknown>>(activeFilters);

  // Sync local filters with prop changes
  useEffect(() => {
    setLocalFilters(activeFilters);
  }, [activeFilters]);

  // Auto-expand sections with active filters
  useEffect(() => {
    const keysWithFilters = Object.keys(activeFilters);
    if (keysWithFilters.length > 0) {
      setExpandedSections(prev => new Set([...prev, ...keysWithFilters]));
    }
  }, [activeFilters]);

  const toggleSection = (key: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleFilterUpdate = useCallback((key: string, value: unknown) => {
    const newFilters = { ...localFilters };
    
    if (value === null || value === undefined || value === '') {
      delete newFilters[key];
    } else {
      newFilters[key] = value;
    }
    
    setLocalFilters(newFilters);
    onFilterChange(newFilters);
  }, [localFilters, onFilterChange]);

  const handleRangeFilter = useCallback((key: string, min: number | null, max: number | null) => {
    if (min === null && max === null) {
      handleFilterUpdate(key, null);
      return;
    }
    
    const rangeFilter: Record<string, number> = {};
    if (min !== null) rangeFilter.$gte = min;
    if (max !== null) rangeFilter.$lte = max;
    
    handleFilterUpdate(key, rangeFilter);
  }, [handleFilterUpdate]);

  // Generate active filter chips
  const getActiveFilterChips = (): FilterChip[] => {
    const chips: FilterChip[] = [];
    
    Object.entries(activeFilters).forEach(([key, value]) => {
      const facet = facets[key];
      const label = facet?.metadata?.label || key;
      
      if (typeof value === 'object' && value !== null) {
        const rangeObj = value as Record<string, number>;
        if ('$gte' in rangeObj || '$lte' in rangeObj) {
          const min = rangeObj.$gte;
          const max = rangeObj.$lte;
          const unit = facet?.metadata?.unit || '';
          chips.push({
            key,
            label,
            value: `${min ?? ''}${min && max ? '-' : ''}${max ?? ''}${unit ? ` ${unit}` : ''}`
          });
        }
      } else {
        chips.push({ key, label, value: String(value) });
      }
    });
    
    return chips;
  };

  const filterChips = getActiveFilterChips();
  const hasFilters = filterChips.length > 0;

  const renderFilter = (key: string, facet: Facet) => {
    const { values, metadata } = facet;
    const isExpanded = expandedSections.has(key);
    const currentValue = localFilters[key];

    // Numeric filter with range
    if (metadata.fieldType === 'number' && values.length > 0) {
      const numericValues = values.filter((v): v is number => typeof v === 'number');
      const min = Math.min(...numericValues);
      const max = Math.max(...numericValues);
      
      const currentMin = typeof currentValue === 'object' && currentValue 
        ? (currentValue as Record<string, number>).$gte 
        : undefined;
      const currentMax = typeof currentValue === 'object' && currentValue 
        ? (currentValue as Record<string, number>).$lte 
        : undefined;

      return (
        <div className="border-b border-gray-100 last:border-b-0">
          <button
            onClick={() => toggleSection(key)}
            className="w-full flex items-center justify-between py-3 px-1 text-left hover:bg-gray-50 transition-colors"
            data-testid={`filter-toggle-${key}`}
          >
            <span className="font-medium text-gray-900 text-sm">
              {metadata.label}
              {metadata.unit && <span className="text-gray-500 ml-1">({metadata.unit})</span>}
            </span>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            )}
          </button>
          
          {isExpanded && (
            <div className="pb-3 px-1 space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder={`Min (${min})`}
                  value={currentMin ?? ''}
                  onChange={(e) => {
                    const val = e.target.value ? Number(e.target.value) : null;
                    handleRangeFilter(key, val, currentMax ?? null);
                  }}
                  className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  data-testid={`filter-min-${key}`}
                />
                <span className="text-gray-400">-</span>
                <input
                  type="number"
                  placeholder={`Max (${max})`}
                  value={currentMax ?? ''}
                  onChange={(e) => {
                    const val = e.target.value ? Number(e.target.value) : null;
                    handleRangeFilter(key, currentMin ?? null, val);
                  }}
                  className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  data-testid={`filter-max-${key}`}
                />
              </div>
              <p className="text-xs text-gray-500">
                Range: {min} - {max} {metadata.unit || ''}
              </p>
            </div>
          )}
        </div>
      );
    }

    // Dropdown/Enum filter
    return (
      <div className="border-b border-gray-100 last:border-b-0">
        <button
          onClick={() => toggleSection(key)}
          className="w-full flex items-center justify-between py-3 px-1 text-left hover:bg-gray-50 transition-colors"
          data-testid={`filter-toggle-${key}`}
        >
          <span className="font-medium text-gray-900 text-sm">
            {metadata.label}
          </span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </button>
        
        {isExpanded && (
          <div className="pb-3 px-1 space-y-1 max-h-48 overflow-y-auto">
            {values.map((value) => (
              <label 
                key={String(value)} 
                className="flex items-center gap-2 py-1 cursor-pointer hover:bg-gray-50 rounded px-1"
              >
                <input
                  type="radio"
                  name={key}
                  checked={currentValue === value}
                  onChange={() => handleFilterUpdate(key, value)}
                  className="text-blue-600 focus:ring-blue-500"
                  data-testid={`filter-option-${key}-${value}`}
                />
                <span className="text-sm text-gray-700">{String(value)}</span>
              </label>
            ))}
            {currentValue && (
              <button
                onClick={() => handleFilterUpdate(key, null)}
                className="text-xs text-blue-600 hover:underline mt-1"
              >
                Clear selection
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  const filterEntries = Object.entries(facets).filter(
    ([, facet]) => facet.metadata?.filterable !== false && facet.values.length > 0
  );

  if (filterEntries.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden" data-testid="filter-panel">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-600" />
            <span className="font-semibold text-gray-900 text-sm">Filters</span>
          </div>
          {hasFilters && (
            <button
              onClick={onClearFilters}
              className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-medium"
              data-testid="clear-all-filters"
            >
              <RotateCcw className="h-3 w-3" />
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Active Filter Chips */}
      {hasFilters && (
        <div className="px-4 py-2 bg-blue-50 border-b border-gray-200">
          <div className="flex flex-wrap gap-1.5">
            {filterChips.map((chip) => (
              <span
                key={chip.key}
                className="inline-flex items-center gap-1 bg-white text-xs text-gray-700 px-2 py-1 rounded border border-gray-200"
              >
                <span className="font-medium">{chip.label}:</span>
                <span>{chip.value}</span>
                <button
                  onClick={() => handleFilterUpdate(chip.key, null)}
                  className="ml-0.5 text-gray-400 hover:text-gray-600"
                  aria-label={`Remove ${chip.label} filter`}
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Filter Options */}
      <div className="px-3 py-1">
        {isLoading && (
          <div className="py-4 text-center text-sm text-gray-500">
            Loading filters...
          </div>
        )}
        {!isLoading && filterEntries.map(([key, facet]) => (
          <div key={key}>
            {renderFilter(key, facet)}
          </div>
        ))}
      </div>
    </div>
  );
}
