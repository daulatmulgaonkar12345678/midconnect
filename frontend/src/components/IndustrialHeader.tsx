'use client';

import Link from 'next/link';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  Menu, X, User, LogOut, Settings, Package, ChevronDown, 
  LayoutDashboard, MapPin, Search, ClipboardList,
  Grid3X3, Loader2, TrendingUp
} from 'lucide-react';
import { APP_NAME } from '@/lib/config';
import { 
  getAutocompleteSuggestions, 
  getLocationSuggestions, 
  getPublicCategoriesList,
  fetchWithAuth 
} from '@/lib/api';

// Industrial color palette
const COLORS = {
  deepBlue: '#0B3C5D',
  deepBlueHover: '#083047',
  lightGrey: '#F5F6F7',
  borderGrey: '#E5E7EB',
  textPrimary: '#1F2937',
  textSecondary: '#6B7280',
};

interface LocationSuggestion {
  label: string;
  type: 'city' | 'state' | 'pincode' | 'pan_india';
  city?: string;
  state?: string;
  pincode?: string;
  seller_count?: number;
}

interface CategoryOption {
  id: string;
  name: string;
  slug: string;
}

export default function IndustrialHeader() {
  const { user, profile, signOut, loading, isAdmin, isSeller, role } = useAuth();
  const isBuyer = role === 'buyer';
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const router = useRouter();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLocation, setSelectedLocation] = useState<LocationSuggestion | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<CategoryOption | null>(null);
  
  // Dropdown states
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  const [showProductDropdown, setShowProductDropdown] = useState(false);
  const [locationSearch, setLocationSearch] = useState('');
  const [locationSuggestions, setLocationSuggestions] = useState<LocationSuggestion[]>([]);
  const [categories, setCategories] = useState<CategoryOption[]>([]);
  const [productSuggestions, setProductSuggestions] = useState<{type: string; text: string; category?: string}[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);

  // Inquiry count for buyers
  const [inquiryCount, setInquiryCount] = useState(0);

  // Refs for click outside
  const locationRef = useRef<HTMLDivElement>(null);
  const categoryRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  
  // Debounce ref for product search
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch buyer inquiries count
  useEffect(() => {
    const fetchInquiryCount = async () => {
      if (!user || !isBuyer) return;
      try {
        const token = await user.getIdToken();
        const data = await fetchWithAuth<{ inquiries?: unknown[]; total?: number }>('/buyer/inquiries?limit=1', token);
        setInquiryCount(data.total || 0);
      } catch (err) {
        console.error('Failed to fetch inquiries:', err);
      }
    };
    fetchInquiryCount();
  }, [user, isBuyer]);

  // Fetch categories
  useEffect(() => {
    const fetchCategories = async () => {
      setLoadingCategories(true);
      try {
        const data = await getPublicCategoriesList();
        const mappedCategories = data.slice(0, 10).map((cat) => ({
          id: cat._id || cat.id,
          name: cat.name,
          slug: cat.slug,
        }));
        setCategories(mappedCategories);
      } catch (err) {
        console.error('Failed to fetch categories:', err);
      } finally {
        setLoadingCategories(false);
      }
    };
    fetchCategories();
  }, []);

  // Fetch location suggestions
  const fetchLocationSuggestionsCallback = useCallback(async (query: string) => {
    setLoadingLocations(true);
    try {
      const data = await getLocationSuggestions(query);
      const suggestions = query.length > 0 ? (data.suggestions || []) : (data.cities || []);
      setLocationSuggestions([
        { label: 'All India', type: 'pan_india' },
        ...suggestions
      ]);
    } catch (err) {
      console.error('Failed to fetch locations:', err);
      setLocationSuggestions([{ label: 'All India', type: 'pan_india' }]);
    } finally {
      setLoadingLocations(false);
    }
  }, []);

  // Fetch product suggestions (autocomplete)
  const fetchProductSuggestionsCallback = useCallback(async (query: string) => {
    if (query.length < 2) {
      setProductSuggestions([]);
      return;
    }
    
    setLoadingProducts(true);
    try {
      const data = await getAutocompleteSuggestions(query);
      setProductSuggestions(data.suggestions || []);
    } catch (err) {
      console.error('Failed to fetch product suggestions:', err);
      setProductSuggestions([]);
    } finally {
      setLoadingProducts(false);
    }
  }, []);

  // Debounced search query effect
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    
    if (searchQuery.length >= 2 && showProductDropdown) {
      debounceRef.current = setTimeout(() => {
        fetchProductSuggestionsCallback(searchQuery);
      }, 300);
    } else {
      setProductSuggestions([]);
    }
    
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, showProductDropdown, fetchProductSuggestionsCallback]);

  // Click outside handlers
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (locationRef.current && !locationRef.current.contains(event.target as Node)) {
        setShowLocationDropdown(false);
      }
      if (categoryRef.current && !categoryRef.current.contains(event.target as Node)) {
        setShowCategoryDropdown(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowProductDropdown(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle search
  const handleSearch = () => {
    const params = new URLSearchParams();
    if (searchQuery) params.set('q', searchQuery);
    if (selectedLocation?.city) params.set('city', selectedLocation.city);
    if (selectedLocation?.state && selectedLocation.type === 'state') params.set('state', selectedLocation.state);
    if (selectedCategory) params.set('category', selectedCategory.id);
    router.push(`/search?${params.toString()}`);
    setIsMenuOpen(false);
    setShowProductDropdown(false);
  };

  // Helper to normalize location selection
  const handleLocationSelect = (loc: LocationSuggestion) => {
    if (loc.type === 'pan_india') {
      setSelectedLocation(null);
    } else {
      // Normalize: ensure city/state always exist
      const labelParts = loc.label.split(',').map(s => s.trim());
      setSelectedLocation({
        ...loc,
        city: loc.city || labelParts[0] || undefined,
        state: loc.state || labelParts[1] || undefined,
      });
    }
    setShowLocationDropdown(false);
    setLocationSearch('');
  };

  // Get icon/badge for location type
  const getLocationTypeIcon = (type: string) => {
    switch (type) {
      case 'city': return '📍';
      case 'state': return '🗺️';
      case 'pincode': return '📮';
      case 'pan_india': return '🇮🇳';
      default: return '📍';
    }
  };

  const handleSignOut = async () => {
    await signOut();
    setIsUserMenuOpen(false);
    router.push('/');
  };

  return (
    <>
      {/* ═══════════════════════════════════════════════════════════════
          LAYER 1: Corporate Utility Header
          ═══════════════════════════════════════════════════════════════ */}
      <header className="bg-white border-b" style={{ borderColor: COLORS.borderGrey }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="flex items-center justify-between h-[60px]">
            
            {/* Left: Logo + B2B Tag */}
            <div className="flex items-center gap-3">
              <Link href="/" className="flex items-center gap-2">
                {/* Industrial Logo Mark */}
                <div 
                  className="w-9 h-9 rounded-md flex items-center justify-center"
                  style={{ backgroundColor: COLORS.deepBlue }}
                >
                  <span className="text-white font-bold text-lg">M</span>
                </div>
                <span 
                  className="text-xl font-semibold hidden sm:inline"
                  style={{ color: COLORS.textPrimary }}
                >
                  {APP_NAME}
                </span>
              </Link>
              
              {/* B2B Tag */}
              <span 
                className="hidden md:inline-flex text-xs font-medium px-2.5 py-1 rounded-full"
                style={{ 
                  backgroundColor: COLORS.lightGrey, 
                  color: COLORS.textSecondary 
                }}
              >
                B2B Marketplace
              </span>
            </div>

            {/* Right: Utility Links */}
            <div className="flex items-center gap-1 sm:gap-3">
              {/* Products Link - Always visible */}
              <Link 
                href="/products"
                className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                style={{ color: COLORS.textSecondary }}
              >
                <Package className="h-4 w-4" />
                <span>Products</span>
              </Link>

              {/* Categories Link - Always visible */}
              <Link 
                href="/categories"
                className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                style={{ color: COLORS.textSecondary }}
              >
                <Grid3X3 className="h-4 w-4" />
                <span>Categories</span>
              </Link>

              {/* Seller Dashboard Link - Only for sellers */}
              {user && isSeller && (
                <Link 
                  href="/seller"
                  className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                  style={{ color: COLORS.textSecondary }}
                >
                  <LayoutDashboard className="h-4 w-4" />
                  <span>Dashboard</span>
                </Link>
              )}

              {/* Admin Panel Link - Only for admins */}
              {user && isAdmin && (
                <Link 
                  href="/admin"
                  className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                  style={{ color: COLORS.textSecondary }}
                >
                  <Settings className="h-4 w-4" />
                  <span>Admin</span>
              </Link>
              )}

              {/* Inquiries Link - ALWAYS visible (left of Login) */}
              <Link 
                href="/inquiries"
                className="hidden sm:flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                style={{ color: COLORS.textSecondary }}
              >
                <ClipboardList className="h-4 w-4" />
                <span>Inquiries</span>
                {user && inquiryCount > 0 && (
                  <span 
                    className="text-xs font-medium px-1.5 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: COLORS.deepBlue }}
                  >
                    {inquiryCount}
                  </span>
                )}
              </Link>

              {/* Divider */}
              <div className="hidden sm:block w-px h-6 bg-gray-200" />

              {/* Auth Section */}
              {!loading && (
                user ? (
                  <div ref={userMenuRef} className="relative">
                    <button
                      onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                      className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-md transition-colors"
                      style={{ color: COLORS.textSecondary }}
                    >
                      <div 
                        className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium"
                        style={{ backgroundColor: COLORS.deepBlue }}
                      >
                        {(profile?.businessName || user.email)?.[0]?.toUpperCase() || 'U'}
                      </div>
                      <span className="hidden sm:inline max-w-[120px] truncate">
                        {profile?.businessName || user.email?.split('@')[0]}
                      </span>
                      <ChevronDown className="h-4 w-4" />
                    </button>

                    {/* User Dropdown */}
                    {isUserMenuOpen && (
                      <div className="absolute right-0 top-full mt-1 w-56 bg-white rounded-md shadow-lg border py-1 z-50" style={{ borderColor: COLORS.borderGrey }}>
                        <div className="px-4 py-3 border-b" style={{ borderColor: COLORS.borderGrey }}>
                          <p className="text-sm font-medium truncate" style={{ color: COLORS.textPrimary }}>
                            {profile?.businessName || 'User'}
                          </p>
                          <p className="text-xs truncate" style={{ color: COLORS.textSecondary }}>{user.email}</p>
                        </div>

                        {isSeller && (
                          <Link href="/seller/listings" className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-50" style={{ color: COLORS.textPrimary }} onClick={() => setIsUserMenuOpen(false)}>
                            <Package className="h-4 w-4" /> My Listings
                          </Link>
                        )}

                        <Link href="/seller/profile" className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-50" style={{ color: COLORS.textPrimary }} onClick={() => setIsUserMenuOpen(false)}>
                          <User className="h-4 w-4" /> Profile
                        </Link>

                        <button onClick={handleSignOut} className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-red-50 w-full text-red-600">
                          <LogOut className="h-4 w-4" /> Sign Out
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Link
                      href="/login"
                      className="px-3 py-2 text-sm font-medium transition-colors hover:bg-gray-50 rounded-md"
                      style={{ color: COLORS.textSecondary }}
                    >
                      Login
                    </Link>
                    <Link
                      href="/register"
                      className="px-4 py-2 text-sm font-medium text-white rounded-md transition-colors"
                      style={{ 
                        backgroundColor: COLORS.deepBlue,
                      }}
                      onMouseOver={(e) => e.currentTarget.style.backgroundColor = COLORS.deepBlueHover}
                      onMouseOut={(e) => e.currentTarget.style.backgroundColor = COLORS.deepBlue}
                    >
                      Register
                    </Link>
                  </div>
                )
              )}

              {/* Mobile Menu Button */}
              <button
                className="lg:hidden p-2 hover:bg-gray-50 rounded-md ml-1"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
              >
                {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ═══════════════════════════════════════════════════════════════
          LAYER 2: Search Engine Header (Always Visible, Sticky)
          ═══════════════════════════════════════════════════════════════ */}
      <div className="bg-white border-b sticky top-0 z-40" style={{ borderColor: COLORS.borderGrey }}>
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-10">
          {/* Desktop: Horizontal layout */}
          <div className="hidden md:flex items-center h-[56px] gap-0">
            
            {/* Location Selector */}
            <div ref={locationRef} className="relative">
              <button
                onClick={() => {
                  setShowLocationDropdown(!showLocationDropdown);
                  if (!showLocationDropdown) fetchLocationSuggestionsCallback('');
                }}
                className="flex items-center gap-2 px-4 h-10 bg-white border rounded-l-md hover:bg-gray-50 transition-colors min-w-[150px]"
                style={{ borderColor: COLORS.borderGrey }}
              >
                <MapPin className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                <span className="text-sm truncate" style={{ color: selectedLocation ? COLORS.textPrimary : COLORS.textSecondary }}>
                  {selectedLocation?.label || 'All India'}
                </span>
                <ChevronDown className="h-4 w-4 ml-auto flex-shrink-0" style={{ color: COLORS.textSecondary }} />
              </button>

              {/* Location Dropdown */}
              {showLocationDropdown && (
                <div 
                  className="absolute left-0 top-full mt-1 w-72 bg-white border rounded-lg shadow-xl"
                  style={{ borderColor: COLORS.borderGrey, zIndex: 9999 }}
                >
                  <div className="p-2 border-b" style={{ borderColor: COLORS.borderGrey }}>
                    <input
                      type="text"
                      value={locationSearch}
                      onChange={(e) => {
                        setLocationSearch(e.target.value);
                        fetchLocationSuggestionsCallback(e.target.value);
                      }}
                      placeholder="Search city, state, pincode..."
                      className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-1"
                      style={{ borderColor: COLORS.borderGrey }}
                      autoComplete="off"
                      autoFocus
                    />
                  </div>
                  <div className="max-h-60 overflow-y-auto py-1">
                    {loadingLocations ? (
                      <div className="px-4 py-3 text-sm text-center" style={{ color: COLORS.textSecondary }}>Loading...</div>
                    ) : (
                      locationSuggestions.map((loc, idx) => (
                        <button
                          key={idx}
                          type="button"
                          data-dropdown-item="location"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleLocationSelect(loc);
                          }}
                          className="w-full px-4 py-2 text-sm text-left hover:bg-gray-50 flex items-center justify-between"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-base">{getLocationTypeIcon(loc.type)}</span>
                            <span style={{ color: COLORS.textPrimary }}>{loc.label}</span>
                            {loc.type !== 'pan_india' && (
                              <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded capitalize" style={{ color: COLORS.textSecondary }}>
                                {loc.type}
                              </span>
                            )}
                          </div>
                          {loc.seller_count !== undefined && loc.seller_count > 0 && (
                            <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                              {loc.seller_count} sellers
                            </span>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Category Dropdown */}
            <div ref={categoryRef} className="relative">
              <button
                onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                className="flex items-center gap-2 px-4 h-10 bg-white border-y border-r hover:bg-gray-50 transition-colors min-w-[160px]"
                style={{ borderColor: COLORS.borderGrey }}
              >
                <Grid3X3 className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                <span className="text-sm truncate" style={{ color: selectedCategory ? COLORS.textPrimary : COLORS.textSecondary }}>
                  {selectedCategory?.name || 'All Categories'}
                </span>
                <ChevronDown className="h-4 w-4 ml-auto flex-shrink-0" style={{ color: COLORS.textSecondary }} />
              </button>

              {/* Category Dropdown */}
              {showCategoryDropdown && (
                <div 
                  className="absolute left-0 top-full mt-1 w-64 bg-white border rounded-lg shadow-xl"
                  style={{ borderColor: COLORS.borderGrey, zIndex: 9999 }}
                >
                  <div className="max-h-60 overflow-y-auto py-1">
                    <button
                      type="button"
                      data-dropdown-item="category"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setSelectedCategory(null);
                        setShowCategoryDropdown(false);
                      }}
                      className="w-full px-4 py-2 text-sm text-left hover:bg-gray-50"
                      style={{ color: COLORS.textPrimary }}
                    >
                      All Categories
                    </button>
                    {loadingCategories ? (
                      <div className="px-4 py-3 text-sm text-center" style={{ color: COLORS.textSecondary }}>Loading...</div>
                    ) : (
                      categories.map((cat) => (
                        <button
                          key={cat.id}
                          type="button"
                          data-dropdown-item="category"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setSelectedCategory(cat);
                            setShowCategoryDropdown(false);
                          }}
                          className="w-full px-4 py-2 text-sm text-left hover:bg-gray-50"
                          style={{ color: COLORS.textPrimary }}
                        >
                          {cat.name}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Search Input with Autocomplete */}
            <div ref={searchRef} className="flex-1 relative">
              <input
                type="text"
                name="search-query-desktop"
                id="search-query-desktop"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowProductDropdown(true)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search industrial products, brands, specifications..."
                className="w-full h-10 px-4 text-sm border-y border-r bg-white focus:outline-none focus:ring-1 focus:ring-inset"
                style={{ borderColor: COLORS.borderGrey }}
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck="false"
                data-lpignore="true"
                data-form-type="other"
                aria-autocomplete="list"
              />

              {/* Product Autocomplete Dropdown */}
              {showProductDropdown && (productSuggestions.length > 0 || loadingProducts) && (
                <div 
                  className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-lg shadow-xl"
                  style={{ borderColor: COLORS.borderGrey, zIndex: 9999 }}
                >
                  {loadingProducts ? (
                    <div className="px-4 py-3 text-sm text-center" style={{ color: COLORS.textSecondary }}>
                      <Loader2 className="h-4 w-4 animate-spin inline mr-2" />
                      Searching...
                    </div>
                  ) : (
                    <div className="max-h-80 overflow-y-auto py-1">
                      {productSuggestions.map((suggestion, idx) => (
                        <button
                          key={idx}
                          type="button"
                          data-dropdown-item="product"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setSearchQuery(suggestion.text);
                            setShowProductDropdown(false);
                          }}
                          className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 flex items-center gap-3"
                        >
                          {suggestion.type === 'product' ? (
                            <Package className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.deepBlue }} />
                          ) : suggestion.type === 'category' ? (
                            <Grid3X3 className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                          ) : (
                            <TrendingUp className="h-4 w-4 flex-shrink-0 text-green-600" />
                          )}
                          <div className="flex-1 min-w-0">
                            <span style={{ color: COLORS.textPrimary }}>{suggestion.text}</span>
                            {suggestion.category && (
                              <span className="ml-2 text-xs" style={{ color: COLORS.textSecondary }}>
                                in {suggestion.category}
                              </span>
                            )}
                          </div>
                          {suggestion.type === 'popular' && (
                            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">Popular</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Search Button */}
            <button
              onClick={handleSearch}
              className="h-10 px-6 flex items-center gap-2 text-white font-medium text-sm rounded-r-md transition-colors"
              style={{ backgroundColor: COLORS.deepBlue }}
              onMouseOver={(e) => e.currentTarget.style.backgroundColor = COLORS.deepBlueHover}
              onMouseOut={(e) => e.currentTarget.style.backgroundColor = COLORS.deepBlue}
            >
              <Search className="h-4 w-4" />
              <span>Search</span>
            </button>
          </div>

          {/* Mobile/Tablet: Vertical compact layout - ALWAYS VISIBLE */}
          <div className="md:hidden py-3 space-y-2">
            {/* Row 1: Location + Category */}
            <div className="flex gap-2">
              {/* Location */}
              <div ref={locationRef} className="relative flex-1">
                <button
                  onClick={() => {
                    setShowLocationDropdown(!showLocationDropdown);
                    if (!showLocationDropdown) fetchLocationSuggestionsCallback('');
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2.5 bg-gray-50 border rounded-md text-sm"
                  style={{ borderColor: COLORS.borderGrey }}
                >
                  <MapPin className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                  <span className="truncate flex-1 text-left" style={{ color: selectedLocation ? COLORS.textPrimary : COLORS.textSecondary }}>
                    {selectedLocation?.label || 'All India'}
                  </span>
                  <ChevronDown className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                </button>

                {/* Mobile Location Dropdown */}
                {showLocationDropdown && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-md shadow-lg z-50 max-h-60 overflow-y-auto" style={{ borderColor: COLORS.borderGrey }}>
                    <div className="p-2 border-b sticky top-0 bg-white" style={{ borderColor: COLORS.borderGrey }}>
                      <input
                        type="text"
                        value={locationSearch}
                        onChange={(e) => {
                          setLocationSearch(e.target.value);
                          fetchLocationSuggestionsCallback(e.target.value);
                        }}
                        placeholder="Search city, state..."
                        className="w-full px-3 py-2 text-sm border rounded-md"
                        style={{ borderColor: COLORS.borderGrey }}
                      />
                    </div>
                    {locationSuggestions.map((loc, idx) => (
                      <button
                        key={idx}
                        type="button"
                        data-dropdown-item="location"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleLocationSelect(loc);
                        }}
                        className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 border-b last:border-b-0 flex justify-between items-center"
                        style={{ borderColor: COLORS.borderGrey, color: COLORS.textPrimary }}
                      >
                        <div className="flex items-center gap-2">
                          <span>{getLocationTypeIcon(loc.type)}</span>
                          <span>{loc.label}</span>
                        </div>
                        {loc.seller_count !== undefined && loc.seller_count > 0 && (
                          <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                            {loc.seller_count}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Category */}
              <div ref={categoryRef} className="relative flex-1">
                <button
                  onClick={() => setShowCategoryDropdown(!showCategoryDropdown)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 bg-gray-50 border rounded-md text-sm"
                  style={{ borderColor: COLORS.borderGrey }}
                >
                  <Grid3X3 className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                  <span className="truncate flex-1 text-left" style={{ color: selectedCategory ? COLORS.textPrimary : COLORS.textSecondary }}>
                    {selectedCategory?.name || 'Category'}
                  </span>
                  <ChevronDown className="h-4 w-4 flex-shrink-0" style={{ color: COLORS.textSecondary }} />
                </button>

                {/* Mobile Category Dropdown */}
                {showCategoryDropdown && (
                  <div 
                    className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-lg shadow-xl max-h-60 overflow-y-auto"
                    style={{ borderColor: COLORS.borderGrey, zIndex: 9999 }}
                  >
                    <button
                      type="button"
                      data-dropdown-item="category"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setSelectedCategory(null);
                        setShowCategoryDropdown(false);
                      }}
                      className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 border-b"
                      style={{ borderColor: COLORS.borderGrey, color: COLORS.textPrimary }}
                    >
                      All Categories
                    </button>
                    {categories.map((cat) => (
                      <button
                        key={cat.id}
                        type="button"
                        data-dropdown-item="category"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setSelectedCategory(cat);
                          setShowCategoryDropdown(false);
                        }}
                        className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 border-b last:border-b-0"
                        style={{ borderColor: COLORS.borderGrey, color: COLORS.textPrimary }}
                      >
                        {cat.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Row 2: Search Input + Button */}
            <div className="flex gap-2 relative">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => setShowProductDropdown(true)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="Search products, brands..."
                  className="w-full px-3 py-2.5 text-sm border rounded-md bg-white"
                  style={{ borderColor: COLORS.borderGrey }}
                  autoComplete="off"
                />

                {/* Mobile Product Autocomplete */}
                {showProductDropdown && (productSuggestions.length > 0 || loadingProducts) && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-md shadow-lg z-50" style={{ borderColor: COLORS.borderGrey }}>
                    {loadingProducts ? (
                      <div className="px-4 py-3 text-sm text-center" style={{ color: COLORS.textSecondary }}>Searching...</div>
                    ) : (
                      <div className="max-h-60 overflow-y-auto py-1">
                        {productSuggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setSearchQuery(suggestion.text);
                              setShowProductDropdown(false);
                            }}
                            className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 flex items-center gap-2"
                          >
                            {suggestion.type === 'product' ? (
                              <Package className="h-4 w-4" style={{ color: COLORS.deepBlue }} />
                            ) : (
                              <TrendingUp className="h-4 w-4 text-green-600" />
                            )}
                            <span className="flex-1" style={{ color: COLORS.textPrimary }}>{suggestion.text}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button
                onClick={handleSearch}
                className="px-4 py-2.5 flex items-center gap-2 text-white font-medium text-sm rounded-md transition-colors"
                style={{ backgroundColor: COLORS.deepBlue }}
              >
                <Search className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════
          MOBILE MENU (Navigation Only - Search is always visible in Layer 2)
          ═══════════════════════════════════════════════════════════════ */}
      {isMenuOpen && (
        <div className="md:hidden fixed inset-x-0 top-[117px] bg-white border-b shadow-lg z-40" style={{ borderColor: COLORS.borderGrey }}>
          <div className="p-4">
            {/* Mobile Navigation */}
            <nav className="space-y-1">
              <Link href="/products" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                Products
              </Link>
              <Link href="/categories" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                Categories
              </Link>
              <Link href="/inquiries" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                Inquiries {user && inquiryCount > 0 && `(${inquiryCount})`}
              </Link>
              
              {user && isSeller && (
                <>
                  <Link href="/seller" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                    Seller Dashboard
                  </Link>
                  <Link href="/seller/listings" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                    My Listings
                  </Link>
                </>
              )}

              {user && isAdmin && (
                <Link href="/admin" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                  Admin Panel
                </Link>
              )}

              <div className="border-t my-2" style={{ borderColor: COLORS.borderGrey }} />

              {!loading && (
                user ? (
                  <>
                    <Link href="/seller/profile" className="block px-4 py-3 text-sm hover:bg-gray-50 rounded-md" style={{ color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                      Profile
                    </Link>
                    <button onClick={handleSignOut} className="block w-full text-left px-4 py-3 text-sm hover:bg-red-50 rounded-md text-red-600">
                      Sign Out
                    </button>
                  </>
                ) : (
                  <div className="space-y-2 pt-2">
                    <Link href="/login" className="block px-4 py-3 text-sm text-center border rounded-md hover:bg-gray-50" style={{ borderColor: COLORS.borderGrey, color: COLORS.textPrimary }} onClick={() => setIsMenuOpen(false)}>
                      Login
                    </Link>
                    <Link href="/register" className="block px-4 py-3 text-sm text-center text-white rounded-md" style={{ backgroundColor: COLORS.deepBlue }} onClick={() => setIsMenuOpen(false)}>
                      Register
                    </Link>
                  </div>
                )
              )}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
