'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search, MapPin, ChevronDown, X, Loader2, TrendingUp, Package, Folder } from 'lucide-react';

// Get API base URL for client-side calls
// Priority: NEXT_PUBLIC_BACKEND_URL > production fallback > relative URL (dev)
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    // Client-side: Check for environment variable first
    const publicUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (publicUrl && publicUrl !== 'undefined' && publicUrl.startsWith('http')) {
      return publicUrl;
    }
    
    // Fallback: Check if we're on Vercel (hostname contains vercel.app)
    // and use the production backend URL
    if (window.location.hostname.includes('vercel.app')) {
      return 'https://b2b-marketplace-v2.preview.emergentagent.com';
    }
    
    // Local development: use relative URLs (Next.js rewrites handle proxy)
    return '';
  }
  // Server-side: Use environment variable
  return process.env.NEXT_PUBLIC_BACKEND_URL || '';
};

interface LocationSuggestion {
  label: string;
  type: 'city' | 'state' | 'pincode' | 'pan_india';
  city?: string;
  state?: string;
  pincode?: string;
  sellerCount?: number;
}

interface ProductSuggestion {
  type: 'product' | 'category' | 'popular' | 'attribute';
  text: string;
  category?: string;
  icon?: string;
}

interface EnterpriseSearchBarProps {
  variant?: 'header' | 'hero' | 'page';
  showLocationFilter?: boolean;
  defaultQuery?: string;
  defaultLocation?: LocationSuggestion | null;
  onSearch?: (query: string, location: LocationSuggestion | null) => void;
  className?: string;
}

export default function EnterpriseSearchBar({
  variant = 'header',
  showLocationFilter = true,
  defaultQuery = '',
  defaultLocation = null,
  onSearch,
  className = ''
}: EnterpriseSearchBarProps) {
  const router = useRouter();
  const [query, setQuery] = useState(defaultQuery);
  const [location, setLocation] = useState<LocationSuggestion | null>(defaultLocation);
  
  // Dropdown states
  const [showProductDropdown, setShowProductDropdown] = useState(false);
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);
  const [productSuggestions, setProductSuggestions] = useState<ProductSuggestion[]>([]);
  const [locationSuggestions, setLocationSuggestions] = useState<LocationSuggestion[]>([]);
  const [locationSearch, setLocationSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  
  const searchRef = useRef<HTMLDivElement>(null);
  const locationRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowProductDropdown(false);
      }
      if (locationRef.current && !locationRef.current.contains(e.target as Node)) {
        setShowLocationDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch product suggestions
  const fetchProductSuggestions = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 2) {
      setProductSuggestions([]);
      return;
    }
    
    setLoading(true);
    try {
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/api/search/autocomplete?q=${encodeURIComponent(searchQuery)}&limit=8`);
      if (res.ok) {
        const data = await res.json();
        setProductSuggestions(data.suggestions || []);
      } else {
        console.error('Autocomplete API error:', res.status, res.statusText);
        setProductSuggestions([]);
      }
    } catch (err) {
      console.error('Autocomplete fetch error:', err);
      setProductSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch location suggestions
  const fetchLocationSuggestions = useCallback(async (searchQuery: string) => {
    setLocationLoading(true);
    try {
      const apiBase = getApiBaseUrl();
      if (searchQuery.length < 1) {
        // Fetch all active seller cities when no query
        const res = await fetch(`${apiBase}/api/search/locations/active?limit=10`);
        if (res.ok) {
          const data = await res.json();
          const cities = data.cities || [];
          // Add Pan India option at the start
          setLocationSuggestions([
            { label: 'Pan India (All Locations)', type: 'pan_india' },
            ...cities
          ]);
        } else {
          setLocationSuggestions([
            { label: 'Pan India (All Locations)', type: 'pan_india' },
          ]);
        }
      } else {
        // Search with query
        const res = await fetch(`${apiBase}/api/search/locations?q=${encodeURIComponent(searchQuery)}&limit=10`);
        if (res.ok) {
          const data = await res.json();
          setLocationSuggestions(data.suggestions || []);
        } else {
          console.error('Location API error:', res.status, res.statusText);
          setLocationSuggestions([]);
        }
      }
    } catch (err) {
      console.error('Location fetch error:', err);
      setLocationSuggestions([
        { label: 'Pan India (All Locations)', type: 'pan_india' },
      ]);
    } finally {
      setLocationLoading(false);
    }
  }, []);

  // Debounced product search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (showProductDropdown) {
        fetchProductSuggestions(query);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, showProductDropdown, fetchProductSuggestions]);

  // Handle search submit
  const handleSearch = () => {
    if (onSearch) {
      onSearch(query, location);
    } else {
      // Navigate to search page with search params
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (location) {
        if (location.type === 'city' && location.city) params.set('city', location.city);
        if (location.type === 'state' && location.state) params.set('state', location.state);
        if (location.type === 'pincode' && location.pincode) params.set('pincode', location.pincode);
        // Don't add param for pan_india - it's the default
      }
      router.push(`/search?${params.toString()}`);
    }
    setShowProductDropdown(false);
    setShowLocationDropdown(false);
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion: ProductSuggestion) => {
    setQuery(suggestion.text);
    setShowProductDropdown(false);
    
    // Auto-search after selection
    setTimeout(() => {
      if (onSearch) {
        onSearch(suggestion.text, location);
      } else {
        const params = new URLSearchParams();
        params.set('q', suggestion.text);
        // Type-based location filter
        if (location) {
          if (location.type === 'city' && location.city) params.set('city', location.city);
          else if (location.type === 'state' && location.state) params.set('state', location.state);
          else if (location.type === 'pincode' && location.pincode) params.set('pincode', location.pincode);
        }
        router.push(`/search?${params.toString()}`);
      }
    }, 100);
  };

  // Handle location select
  const handleLocationSelect = (loc: LocationSuggestion) => {
    setLocation(loc);
    setShowLocationDropdown(false);
    setLocationSearch('');
  };

  // Get icon for suggestion type
  const getSuggestionIcon = (type: string) => {
    switch (type) {
      case 'product': return <Package className="h-4 w-4 text-blue-500" />;
      case 'category': return <Folder className="h-4 w-4 text-purple-500" />;
      case 'popular': return <TrendingUp className="h-4 w-4 text-green-500" />;
      default: return <Search className="h-4 w-4 text-gray-400" />;
    }
  };

  // Styles based on variant
  const containerStyles = variant === 'hero' 
    ? 'bg-white rounded-xl shadow-xl border border-gray-200 p-2'
    : variant === 'page'
    ? 'bg-white rounded-xl shadow-lg border border-gray-200 p-3 overflow-hidden'
    : 'bg-white rounded-lg border border-gray-200 overflow-hidden';

  return (
    <div className={`${containerStyles} ${className}`}>
      <div className={`flex items-center gap-2 ${variant === 'hero' ? 'flex-col md:flex-row' : ''}`}>
        
        {/* Product Search Input */}
        <div ref={searchRef} className={`relative ${variant === 'hero' ? 'w-full md:flex-1' : 'flex-1'}`}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setShowProductDropdown(true)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search products, categories..."
              className={`w-full pl-10 pr-4 ${variant === 'header' ? 'py-2.5' : 'py-3.5'} bg-gray-50 border-0 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition`}
              data-testid="search-product-input"
            />
            {loading && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 animate-spin" />
            )}
          </div>
          
          {/* Product Suggestions Dropdown */}
          {showProductDropdown && (query.length >= 2 || productSuggestions.length > 0) && (
            <div className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl max-h-80 overflow-hidden">
              {productSuggestions.length === 0 && query.length >= 2 && !loading ? (
                <div className="px-4 py-8 text-center">
                  <Search className="h-8 w-8 mx-auto text-gray-300 mb-2" />
                  <p className="text-gray-500 text-sm">No suggestions for "{query}"</p>
                  <p className="text-gray-400 text-xs mt-1">Press Enter to search anyway</p>
                </div>
              ) : (
                <div className="py-2">
                  {productSuggestions.map((suggestion, idx) => (
                    <button
                      key={`${suggestion.type}-${idx}`}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="w-full px-4 py-3 text-left hover:bg-blue-50 flex items-center gap-3 transition"
                    >
                      {getSuggestionIcon(suggestion.type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-gray-900 font-medium truncate">{suggestion.text}</p>
                        {suggestion.category && (
                          <p className="text-xs text-gray-500">in {suggestion.category}</p>
                        )}
                      </div>
                      {suggestion.type === 'popular' && (
                        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">Popular</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Divider */}
        {showLocationFilter && (
          <div className={`hidden md:block w-px h-8 bg-gray-200 ${variant === 'hero' ? 'md:block' : ''}`} />
        )}

        {/* Location Dropdown */}
        {showLocationFilter && (
          <div ref={locationRef} className={`relative ${variant === 'hero' ? 'w-full md:w-64' : 'w-48'}`}>
            <button
              type="button"
              onClick={() => {
                setShowLocationDropdown(!showLocationDropdown);
                if (!showLocationDropdown) {
                  fetchLocationSuggestions(locationSearch);
                }
              }}
              className={`w-full flex items-center gap-2 px-3 ${variant === 'header' ? 'py-2.5' : 'py-3.5'} bg-gray-50 rounded-lg hover:bg-gray-100 transition text-left`}
              data-testid="search-location-dropdown"
            >
              <MapPin className="h-5 w-5 text-gray-400 flex-shrink-0" />
              <span className={`flex-1 truncate ${location ? 'text-gray-900' : 'text-gray-500'}`}>
                {location?.label || 'All India'}
              </span>
              <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showLocationDropdown ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Location Dropdown */}
            {showLocationDropdown && (
              <div className="absolute z-50 w-full md:w-72 right-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-xl max-h-80 overflow-hidden">
                {/* Search Input */}
                <div className="p-3 border-b border-gray-100">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={locationSearch}
                      onChange={(e) => {
                        setLocationSearch(e.target.value);
                        fetchLocationSuggestions(e.target.value);
                      }}
                      placeholder="Search city, state, or pincode..."
                      className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-blue-500"
                      autoFocus
                    />
                  </div>
                </div>
                
                {/* Quick Options */}
                <div className="p-2 border-b border-gray-100">
                  <button
                    onClick={() => handleLocationSelect({ label: 'Pan India (All Locations)', type: 'pan_india' })}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-blue-50 rounded-lg flex items-center gap-2"
                  >
                    <span className="text-lg">🇮🇳</span>
                    <span className="font-medium">Pan India</span>
                    <span className="text-gray-400 text-xs ml-auto">All locations</span>
                  </button>
                </div>
                
                {/* Location Suggestions */}
                <div className="max-h-48 overflow-y-auto py-2">
                  {locationLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                    </div>
                  ) : locationSuggestions.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-gray-500 text-center">
                      {locationSearch ? 'No locations found' : 'Type to search locations'}
                    </p>
                  ) : (
                    locationSuggestions.filter(l => l.type !== 'pan_india').map((loc, idx) => (
                      <button
                        key={`${loc.type}-${idx}`}
                        onClick={() => handleLocationSelect(loc)}
                        className="w-full px-4 py-2.5 text-left hover:bg-blue-50 flex items-center gap-3"
                      >
                        <MapPin className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-900 truncate">{loc.label}</p>
                          <p className="text-xs text-gray-500 capitalize">{loc.type}</p>
                        </div>
                        {loc.sellerCount !== undefined && loc.sellerCount > 0 && (
                          <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">
                            {loc.sellerCount} sellers
                          </span>
                        )}
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Search Button */}
        <button
          onClick={handleSearch}
          className={`flex items-center gap-2 px-5 ${variant === 'header' ? 'py-2.5' : 'py-3.5'} bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium ${variant === 'hero' ? 'w-full md:w-auto justify-center' : ''}`}
          data-testid="search-submit-btn"
        >
          <Search className="h-5 w-5" />
          <span className={variant === 'header' ? 'hidden lg:inline' : ''}>Search</span>
        </button>
      </div>
      
      {/* Selected Location Chip - More Prominent */}
      {location && location.type !== 'pan_india' && (
        <div className="flex items-center gap-2 px-4 py-2 -mx-4 -mb-2 bg-slate-50 border-t border-slate-200 rounded-b-xl">
          <span className="text-sm font-medium text-slate-600">Filtering by:</span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-full shadow-sm">
            <MapPin className="h-4 w-4" />
            {location.label}
            <button
              onClick={() => {
                setLocation(null);
                setLocationSearch('');
              }}
              className="ml-1 hover:bg-blue-700 rounded-full p-0.5 transition-colors"
              data-testid="clear-location-btn"
              aria-label="Remove location filter"
            >
              <X className="h-4 w-4" />
            </button>
          </span>
        </div>
      )}
    </div>
  );
}
