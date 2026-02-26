'use client';

import Link from 'next/link';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  Menu, X, User, LogOut, Settings, Package, ChevronDown, 
  LayoutDashboard, MapPin, Search, FileText, ClipboardList,
  Grid3X3
} from 'lucide-react';
import { APP_NAME } from '@/lib/config';

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

// Get API base URL
const getApiBaseUrl = (): string => {
  if (typeof window !== 'undefined') {
    const publicUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (publicUrl && publicUrl.startsWith('http')) return publicUrl;
    if (window.location.hostname.includes('vercel.app')) {
      return 'https://b2b-marketplace-v2.preview.emergentagent.com';
    }
    return '';
  }
  return process.env.NEXT_PUBLIC_BACKEND_URL || '';
};

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
        const apiBase = getApiBaseUrl();
        const token = await user.getIdToken();
        const res = await fetch(`${apiBase}/api/inquiries/buyer`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setInquiryCount(Array.isArray(data) ? data.length : 0);
        }
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
        const apiBase = getApiBaseUrl();
        const res = await fetch(`${apiBase}/api/categories`);
        if (res.ok) {
          const data = await res.json();
          setCategories(data.slice(0, 10)); // Limit to 10 categories
        }
      } catch (err) {
        console.error('Failed to fetch categories:', err);
      } finally {
        setLoadingCategories(false);
      }
    };
    fetchCategories();
  }, []);

  // Fetch location suggestions
  const fetchLocationSuggestions = useCallback(async (query: string) => {
    setLoadingLocations(true);
    try {
      const apiBase = getApiBaseUrl();
      const endpoint = query.length > 0 
        ? `${apiBase}/api/search/locations?q=${encodeURIComponent(query)}&limit=8`
        : `${apiBase}/api/search/locations/active?limit=8`;
      
      const res = await fetch(endpoint);
      if (res.ok) {
        const data = await res.json();
        const suggestions = query.length > 0 ? (data.suggestions || []) : (data.cities || []);
        setLocationSuggestions([
          { label: 'All India', type: 'pan_india' },
          ...suggestions
        ]);
      }
    } catch (err) {
      console.error('Failed to fetch locations:', err);
      setLocationSuggestions([{ label: 'All India', type: 'pan_india' }]);
    } finally {
      setLoadingLocations(false);
    }
  }, []);

  // Fetch product suggestions (autocomplete)
  const fetchProductSuggestions = useCallback(async (query: string) => {
    if (query.length < 2) {
      setProductSuggestions([]);
      return;
    }
    
    setLoadingProducts(true);
    try {
      const apiBase = getApiBaseUrl();
      const res = await fetch(`${apiBase}/api/search/autocomplete?q=${encodeURIComponent(query)}&limit=8`);
      if (res.ok) {
        const data = await res.json();
        setProductSuggestions(data.suggestions || []);
      } else {
        setProductSuggestions([]);
      }
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
        fetchProductSuggestions(searchQuery);
      }, 300);
    } else {
      setProductSuggestions([]);
    }
    
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, showProductDropdown, fetchProductSuggestions]);

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
    document.addEventListener('mousedown', handleClickOutside);
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
                  if (!showLocationDropdown) fetchLocationSuggestions('');
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
                <div className="absolute left-0 top-full mt-1 w-72 bg-white border rounded-md shadow-lg z-50" style={{ borderColor: COLORS.borderGrey }}>
                  <div className="p-2 border-b" style={{ borderColor: COLORS.borderGrey }}>
                    <input
                      type="text"
                      value={locationSearch}
                      onChange={(e) => {
                        setLocationSearch(e.target.value);
                        fetchLocationSuggestions(e.target.value);
                      }}
                      placeholder="Search city, state..."
                      className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-1"
                      style={{ borderColor: COLORS.borderGrey }}
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
                          onClick={() => {
                            setSelectedLocation(loc.type === 'pan_india' ? null : loc);
                            setShowLocationDropdown(false);
                            setLocationSearch('');
                          }}
                          className="w-full px-4 py-2 text-sm text-left hover:bg-gray-50 flex items-center justify-between"
                        >
                          <span style={{ color: COLORS.textPrimary }}>{loc.label}</span>
                          {loc.seller_count && (
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
                <div className="absolute left-0 top-full mt-1 w-64 bg-white border rounded-md shadow-lg z-50" style={{ borderColor: COLORS.borderGrey }}>
                  <div className="max-h-60 overflow-y-auto py-1">
                    <button
                      onClick={() => {
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
                          onClick={() => {
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
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setShowProductDropdown(true)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search industrial products, brands, specifications..."
                className="w-full h-10 px-4 text-sm border-y border-r bg-white focus:outline-none focus:ring-1 focus:ring-inset"
                style={{ borderColor: COLORS.borderGrey }}
                autoComplete="off"
              />

              {/* Product Autocomplete Dropdown */}
              {showProductDropdown && (productSuggestions.length > 0 || loadingProducts) && (
                <div className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-md shadow-lg z-50" style={{ borderColor: COLORS.borderGrey }}>
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
                          onClick={() => {
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
                    if (!showLocationDropdown) fetchLocationSuggestions('');
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
                          fetchLocationSuggestions(e.target.value);
                        }}
                        placeholder="Search city, state..."
                        className="w-full px-3 py-2 text-sm border rounded-md"
                        style={{ borderColor: COLORS.borderGrey }}
                      />
                    </div>
                    {locationSuggestions.map((loc, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setSelectedLocation(loc.type === 'pan_india' ? null : loc);
                          setShowLocationDropdown(false);
                          setLocationSearch('');
                        }}
                        className="w-full px-4 py-2.5 text-sm text-left hover:bg-gray-50 border-b last:border-b-0 flex justify-between items-center"
                        style={{ borderColor: COLORS.borderGrey, color: COLORS.textPrimary }}
                      >
                        <span>{loc.label}</span>
                        {loc.seller_count && (
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
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border rounded-md shadow-lg z-50 max-h-60 overflow-y-auto" style={{ borderColor: COLORS.borderGrey }}>
                    <button
                      onClick={() => {
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
                        onClick={() => {
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
            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search products, brands..."
                className="flex-1 px-3 py-2.5 text-sm border rounded-md bg-white"
                style={{ borderColor: COLORS.borderGrey }}
              />
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
