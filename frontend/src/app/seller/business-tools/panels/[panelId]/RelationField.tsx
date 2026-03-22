'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Link2, X, Loader2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface RelationOption {
  id: string;
  label: string;
  sub?: string;
}

interface RelationFieldProps {
  panelId: string;
  fieldKey: string;
  relatedPanel: string;
  value: string;
  resolvedLabel?: string;
  resolvedSub?: string;
  token: string;
  onChange: (id: string, label: string) => void;
}

export function RelationField({
  panelId,
  fieldKey,
  relatedPanel,
  value,
  resolvedLabel,
  resolvedSub,
  token,
  onChange,
}: RelationFieldProps) {
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState<RelationOption[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState(resolvedLabel || '');
  const [selectedSub, setSelectedSub] = useState(resolvedSub || '');
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const placeholderMap: Record<string, string> = {
    inventory: 'Search products...',
    invoices: 'Search invoices...',
    buyers: 'Search buyers...',
    suppliers: 'Search suppliers...',
    purchase_orders: 'Search purchase orders...',
    quotations: 'Search quotations...',
    composite_products: 'Search composite products...',
    employees: 'Search employees...',
  };
  const placeholder = placeholderMap[relatedPanel] || 'Search records...';

  // Sync resolved label from parent (e.g. when editing existing record)
  useEffect(() => {
    if (resolvedLabel) setSelectedLabel(resolvedLabel);
    if (resolvedSub) setSelectedSub(resolvedSub);
  }, [resolvedLabel, resolvedSub]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchOptions = useCallback(async (searchQuery: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ target: relatedPanel, search: searchQuery });
      const res = await fetch(
        `${API_URL}/api/business-tools/panels/${panelId}/relation-lookup?${params}`,
        { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
      );
      if (res.ok) {
        const data = await res.json();
        setOptions(data.results || []);
      }
    } catch { /* empty */ }
    setIsLoading(false);
  }, [panelId, relatedPanel, token]);

  const handleSearchChange = (val: string) => {
    setQuery(val);
    setIsOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchOptions(val), 300);
  };

  const handleFocus = () => {
    setIsOpen(true);
    // Fetch initial results on focus if none loaded
    if (options.length === 0) fetchOptions(query);
  };

  const handleSelect = (opt: RelationOption) => {
    onChange(opt.id, opt.label);
    setSelectedLabel(opt.label);
    setSelectedSub(opt.sub || '');
    setQuery('');
    setIsOpen(false);
    setOptions([]);
  };

  const handleClear = () => {
    onChange('', '');
    setSelectedLabel('');
    setSelectedSub('');
    setQuery('');
    setOptions([]);
  };

  return (
    <div ref={wrapperRef} className="relative" data-testid={`relation-field-${fieldKey}`}>
      {/* Selected value chip */}
      {value && selectedLabel && (
        <div className="flex items-center gap-2 mb-2 px-3 py-2 bg-indigo-50 rounded-lg border border-indigo-100">
          <Link2 className="h-4 w-4 text-indigo-500 flex-shrink-0" />
          <span className="text-sm text-indigo-700 flex-1 truncate">
            {selectedLabel}
            {selectedSub && <span className="text-indigo-400 ml-1">({selectedSub})</span>}
          </span>
          <button onClick={handleClear} className="text-gray-400 hover:text-red-500 flex-shrink-0" data-testid={`relation-clear-${fieldKey}`}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={e => handleSearchChange(e.target.value)}
          onFocus={handleFocus}
          placeholder={value && selectedLabel ? 'Search to change...' : placeholder}
          className="w-full pl-9 pr-8 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          data-testid={`input-${fieldKey}-search`}
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400 animate-spin" />
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-20 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto" data-testid={`relation-dropdown-${fieldKey}`}>
          {isLoading && options.length === 0 ? (
            <div className="flex items-center justify-center gap-2 px-3 py-4 text-sm text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading...
            </div>
          ) : options.length === 0 ? (
            <div className="px-3 py-4 text-sm text-gray-400 text-center" data-testid={`relation-empty-${fieldKey}`}>
              No results found
            </div>
          ) : (
            options.map(opt => (
              <button
                key={opt.id}
                onClick={() => handleSelect(opt)}
                className="w-full text-left px-3 py-2.5 hover:bg-indigo-50 text-sm flex items-center justify-between border-b last:border-b-0 transition-colors"
                data-testid={`relation-option-${opt.id}`}
              >
                <span className="font-medium text-gray-800 truncate">{opt.label}</span>
                {opt.sub && <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{opt.sub}</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
