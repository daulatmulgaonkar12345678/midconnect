/**
 * Production-Ready API Client for Next.js Website
 * 
 * SSOT: Pure API client layer - all domain types imported from @/types
 * 
 * Features:
 * - Centralized API logic
 * - Proper error handling
 * - Request timeout with cold-start support
 * - Auth token management
 * - Input sanitization
 * - No duplicate types
 * - No snake_case fields
 * - No legacy endpoints
 */

import { ApiError, ApiResponse } from '@/types/api';
import type {
  Category,
  Product,
  ProductWithSellers,
  ProductSeller,
  ProductWithAllSellers,
  SellerListing,
  BuyerInquiry,
  SellerInquiry,
  PricingTier,
  PricingSlab,
  PricingTierCreate,
  AdminInquiry,
  SearchListing,
  AdminProduct,
  AdminSpecTemplate,
  AdminStats,
  AdminUser,
  SellerSubscriptionStatus,
  SubscriptionDetails,
  B2BCategory,
  B2BSpecTemplate,
  SpecFieldDefinition,
  GlobalDropdown,
  DropdownValue,
  CategorySettings,
  Manufacturer,
  SellerStats,
  AdminAnalytics,
  AdminKPIMetrics,
  SellerRequest,
  UserProfile,
  TechnicalSpec,
  SellerInquiriesResponse,
} from '@/types';

// Re-export types for backwards compatibility with existing imports
export type {
  Category,
  Product,
  ProductWithSellers,
  ProductSeller,
  ProductWithAllSellers,
  SellerListing,
  BuyerInquiry,
  SellerInquiry,
  PricingTier,
  PricingSlab,
  PricingTierCreate,
  AdminInquiry,
  AdminProduct,
  AdminSpecTemplate,
  AdminStats,
  AdminUser,
  SellerSubscriptionStatus,
  SubscriptionDetails,
  B2BCategory,
  B2BSpecTemplate,
  SpecFieldDefinition,
  GlobalDropdown,
  DropdownValue,
  CategorySettings,
  Manufacturer,
  SellerStats,
  AdminAnalytics,
  AdminKPIMetrics,
  SellerRequest,
  UserProfile,
  TechnicalSpec,
};

// API Configuration - uses environment variable with fallback for Vercel
const getApiUrl = (): string => {
  // ENTERPRISE FIX: Support multiple environment variable names for backwards compatibility
  // Priority: NEXT_PUBLIC_API_URL > NEXT_PUBLIC_API_BASE_URL > NEXT_PUBLIC_BACKEND_URL
  const apiUrl = 
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||  // Legacy fallback
    process.env.NEXT_PUBLIC_BACKEND_URL;
  
  if (apiUrl && apiUrl.startsWith('http')) {
    return apiUrl;
  }
  
  // Production domain fallback for udyogconnect.in
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    
    // Production domains - use Render backend
    if (hostname === 'udyogconnect.in' || hostname === 'www.udyogconnect.in') {
      return 'https://midconnect.onrender.com';
    }
    
    // Vercel preview deployments
    if (hostname.includes('vercel.app') || hostname.includes('midconnect')) {
      return 'https://midconnect.onrender.com';
    }
  }
  
  // Local development - use relative URLs (will be proxied by Next.js)
  return '';
};

const API_URL = getApiUrl();

// Log API URL configuration for debugging (only in browser)
if (typeof window !== 'undefined') {
  console.log('[API Config] API_URL:', API_URL || '(relative/proxy)');
  if (!API_URL && !window.location.hostname.includes('localhost')) {
    console.warn('[API Config] No API URL configured - using domain fallback or proxy');
  }
}

const DEFAULT_TIMEOUT = 30000; // 30 seconds

// ==================== Input Sanitization ====================

export function sanitizeInput(input: string): string {
  if (typeof input !== 'string') return '';
  return input
    .trim()
    .slice(0, 1000)
    .replace(/[<>]/g, '');
}

export function sanitizeObject<T extends Record<string, unknown>>(obj: T): T {
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'string') {
      sanitized[key] = sanitizeInput(value);
    } else if (value !== null && value !== undefined) {
      sanitized[key] = value;
    }
  }
  return sanitized as T;
}

// ==================== Cold-Start & Retry Configuration ====================

const COLD_START_TIMEOUT = 60000;
const MAX_RETRIES = 3;
const RETRY_DELAYS = [2000, 4000, 8000];
const COLD_START_RETRY_DELAYS = [3000, 6000, 12000];

let isServerWaking = false;
let serverWarmedUp = false;
let lastSuccessfulRequest = Date.now();
const SERVER_SLEEP_THRESHOLD = 10 * 60 * 1000;

export async function warmBackend(): Promise<{ ready: boolean; message: string }> {
  if (serverWarmedUp && !mightBeColdStart()) {
    return { ready: true, message: 'Server is ready' };
  }
  
  const healthUrl = `${API_URL}/api/health`;
  
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        serverWarmedUp = true;
        isServerWaking = false;
        lastSuccessfulRequest = Date.now();
        return { ready: true, message: 'Server is ready' };
      }
    } catch {
      console.log(`[API] Health check attempt ${attempt + 1}/3 - server may be waking up`);
      isServerWaking = true;
      
      if (attempt < 2) {
        await delay(RETRY_DELAYS[attempt] || 2000);
      }
    }
  }
  
  return { ready: false, message: 'Server is waking up, please wait...' };
}

function getRetryDelay(attempt: number): number {
  const delays = isServerWaking ? COLD_START_RETRY_DELAYS : RETRY_DELAYS;
  return delays[attempt] || delays[delays.length - 1];
}

function mightBeColdStart(): boolean {
  return Date.now() - lastSuccessfulRequest > SERVER_SLEEP_THRESHOLD;
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isRetryableError(error: unknown): boolean {
  if (error instanceof ApiError) {
    if (error.status === 400 || error.status === 401 || error.status === 403) {
      return false;
    }
    return error.status >= 500 || error.status === 0 || error.status === 408;
  }
  if (error instanceof Error) {
    return error.name === 'AbortError' || 
           error.message.includes('fetch') ||
           error.message.includes('network') ||
           error.message.includes('ECONNREFUSED');
  }
  return false;
}

function shouldSkipRetry(endpoint: string): boolean {
  const noRetryEndpoints = ['/users/register', '/auth/register'];
  return noRetryEndpoints.some(path => endpoint.includes(path));
}

// ==================== Core Fetch Function ====================

interface FetchOptions extends Omit<RequestInit, 'body'> {
  timeout?: number;
  body?: unknown;
  retries?: number;
  skipRetry?: boolean;
}

async function fetchAPI<T = unknown>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { 
    timeout = mightBeColdStart() ? COLD_START_TIMEOUT : DEFAULT_TIMEOUT, 
    body, 
    retries = MAX_RETRIES,
    skipRetry = shouldSkipRetry(endpoint),
    ...fetchOptions 
  } = options;
  
  if (!API_URL) {
    throw new ApiError('API URL not configured', 500, 'CONFIG_ERROR');
  }

  // Ensure endpoint starts with /api for backend routing
  let sanitizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  if (!sanitizedEndpoint.startsWith('/api')) {
    sanitizedEndpoint = `/api${sanitizedEndpoint}`;
  }
  const url = `${API_URL}${sanitizedEndpoint}`;

  let lastError: Error | null = null;
  const maxAttempts = skipRetry ? 1 : retries + 1;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...fetchOptions.headers,
        },
        body: body ? JSON.stringify(body) : undefined,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData: { detail?: string; message?: string; errorCode?: string } = {};
        
        try {
          errorData = await response.json();
        } catch {
          errorData = { detail: `HTTP ${response.status}` };
        }

        const error = new ApiError(
          errorData.detail || errorData.message || `Request failed with status ${response.status}`,
          response.status,
          errorData.errorCode
        );

        if (attempt < maxAttempts && isRetryableError(error)) {
          lastError = error;
          const retryDelay = getRetryDelay(attempt);
          console.log(`[API] Retry ${attempt + 1}/${maxAttempts} for ${endpoint} after ${retryDelay}ms`);
          await delay(retryDelay);
          continue;
        }

        throw error;
      }

      lastSuccessfulRequest = Date.now();
      serverWarmedUp = true;
      isServerWaking = false;

      const text = await response.text();
      if (!text) return {} as T;
      
      return JSON.parse(text);
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof Error) {
        lastError = error;
        
        if (error.name === 'AbortError') {
          if (attempt === 1 && mightBeColdStart()) {
            isServerWaking = true;
            console.log('[API] Server may be waking up, retrying with extended timeout...');
          }
        }

        if (attempt < maxAttempts && isRetryableError(error)) {
          const retryDelay = getRetryDelay(attempt);
          console.log(`[API] Retry ${attempt + 1}/${maxAttempts} for ${endpoint} after ${retryDelay}ms`);
          await delay(retryDelay);
          continue;
        }

        if (error.name === 'AbortError') {
          throw new ApiError(
            isServerWaking 
              ? 'Server is starting up. Please wait a moment and try again.'
              : 'Request timeout. Please try again.',
            408,
            'TIMEOUT'
          );
        }
        throw new ApiError(error.message || 'Network error', 0, 'NETWORK_ERROR');
      }

      throw new ApiError('Unknown error occurred', 0, 'UNKNOWN');
    }
  }

  throw lastError || new ApiError('Request failed after retries', 0, 'RETRY_EXHAUSTED');
}

export async function fetchWithAuth<T = unknown>(
  endpoint: string,
  token: string,
  options: FetchOptions = {}
): Promise<T> {
  if (!token) {
    throw new ApiError('Authentication required', 401, 'AUTH_REQUIRED');
  }

  return fetchAPI<T>(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });
}

// ==================== Health Check ====================

export const checkHealth = () => fetchAPI<{ status: string }>('/health', { skipRetry: true });
export const checkReadiness = () => fetchAPI<{
  mongodb: { status: string };
  firebase: { status: string };
  overall: string;
}>('/health/ready', { skipRetry: true });

export async function warmupBackend(): Promise<boolean> {
  try {
    await checkHealth();
    lastSuccessfulRequest = Date.now();
    isServerWaking = false;
    return true;
  } catch {
    isServerWaking = true;
    return false;
  }
}

export async function waitForBackend(maxWaitMs: number = 30000): Promise<boolean> {
  const startTime = Date.now();
  const checkInterval = 2000;
  
  while (Date.now() - startTime < maxWaitMs) {
    if (await warmupBackend()) {
      return true;
    }
    await delay(checkInterval);
  }
  
  return false;
}

// ==================== Public API ====================

// Alias for public API calls without auth
export const fetchBase = fetchAPI;

// ==================== SEARCH HELPERS ====================

interface AutocompleteSuggestion {
  type: 'product' | 'category' | 'popular' | 'attribute';
  text: string;
  category?: string;
  icon?: string;
}

interface AutocompleteResponse {
  suggestions: AutocompleteSuggestion[];
  query?: string;
  correctedQuery?: string;
  didYouMean?: string;
}

interface LocationSuggestion {
  label: string;
  type: 'city' | 'state' | 'pincode' | 'pan_india';
  city?: string;
  state?: string;
  pincode?: string;
  seller_count?: number;
  sellerCount?: number;
}

interface LocationSearchResponse {
  suggestions?: LocationSuggestion[];
  cities?: LocationSuggestion[];
}

interface PublicCategory {
  _id: string;
  id: string;
  name: string;
  slug: string;
  productCount?: number;
  listingCount?: number;
}

export const getAutocompleteSuggestions = (query: string): Promise<AutocompleteResponse> =>
  fetchAPI<AutocompleteResponse>(`/search/autocomplete?q=${encodeURIComponent(query)}&limit=8`);

export const getLocationSuggestions = (query?: string): Promise<LocationSearchResponse> =>
  fetchAPI<LocationSearchResponse>(
    query && query.length > 0
      ? `/search/locations?q=${encodeURIComponent(query)}&limit=8`
      : `/search/locations/active?limit=8`
  );

export const getPublicCategoriesList = (): Promise<PublicCategory[]> =>
  fetchAPI<PublicCategory[]>('/categories');

// ==================== CATEGORIES ====================

export const getCategories = (): Promise<Category[]> => 
  fetchAPI<Category[]>('/categories/all');

export const getPublicCategories = (): Promise<{
  _id: string;
  name: string;
  slug?: string;  // SEO v2.1: Added for slug-based routing
  image?: string;
  icon?: string;
  productCount: number;
  listingCount: number;
}[]> => fetchAPI('/categories/public');

export const getAllCategories = getCategories;

export const getProducts = (categoryId?: string): Promise<{
  _id: string;
  name: string;
  slug: string;
  description?: string;
  categoryId?: string;
  categoryName?: string;
  images?: string[];
  sellerCount: number;
  minPrice?: number;
}[]> => {
  const params = categoryId ? `?categoryId=${encodeURIComponent(categoryId)}` : '';
  return fetchAPI(`/products${params}`);
};

export const getProduct = (productId: string): Promise<ProductWithSellers> => 
  fetchAPI<ProductWithSellers>(`/products/${encodeURIComponent(productId)}`);

export const getProductWithSellers = (productIdentifier: string): Promise<ProductWithAllSellers> =>
  fetchAPI<ProductWithAllSellers>(`/products/detail/${encodeURIComponent(productIdentifier)}`);

export interface SearchResult {
  products: SearchListing[];
  total: number;
  guidanceDisclaimer?: string;
}

// Backend search response has 'listings' key, we need to map it to 'products'
interface BackendSearchResponse {
  listings: SearchListing[];
  total: number;
  guidanceDisclaimer?: string;
}

export async function searchProducts(
  query: string,
  options?: {
    categoryId?: string;
    city?: string;
    state?: string;
    pincode?: string;
    lat?: number;
    lng?: number;
    radius_km?: number;
    limit?: number;
    skip?: number;
  }
): Promise<SearchResult> {
  const sanitizedQuery = sanitizeInput(query);
  const params = new URLSearchParams();

  params.append("q", sanitizedQuery);

  if (options?.categoryId) params.append("category", options.categoryId);
  if (options?.city) params.append("city", options.city);
  if (options?.state) params.append("state", options.state);
  if (options?.pincode) params.append("pincode", options.pincode);
  if (options?.lat) params.append("lat", options.lat.toString());
  if (options?.lng) params.append("lng", options.lng.toString());
  if (options?.radius_km) params.append("radius_km", options.radius_km.toString());
  if (options?.limit) params.append("limit", Math.min(options.limit, 100).toString());
  if (options?.skip) params.append("skip", Math.max(options.skip, 0).toString());

  const response = await fetchAPI<BackendSearchResponse>(`/search?${params.toString()}`);
  
  // Transform backend response to expected format
  return {
    products: response.listings || [],
    total: response.total || 0,
    guidanceDisclaimer: response.guidanceDisclaimer,
  };
}

// ==================== GEO SEARCH API ====================

interface GeoSearchResponse {
  listings: SearchListing[];
  total: number;
  hasMore: boolean;
  fallbackUsed: 'radius' | 'state' | 'pan_india' | null;
  message: string | null;
  searchedLocation: {
    city: string | null;
    state: string | null;
    lat: number | null;
    lng: number | null;
    radius_km: number;
  };
  search_time_ms: number;
  // Smart search fields
  didYouMean?: string;
  correctedQuery?: string;
  originalQuery?: string;
  autoCorreced?: boolean;
}

export interface GeoSearchResult {
  products: SearchListing[];
  total: number;
  hasMore: boolean;
  fallbackUsed: 'radius' | 'state' | 'pan_india' | null;
  fallbackMessage: string | null;
  // Smart search fields
  didYouMean?: string;
  correctedQuery?: string;
  originalQuery?: string;
  autoCorreced?: boolean;
}

export async function geoSearchProducts(options: {
  query?: string;
  city?: string;
  state?: string;
  lat?: number;
  lng?: number;
  radiusKm?: number;
  categoryId?: string;
  minPrice?: number;
  maxPrice?: number;
  inStock?: boolean;
  limit?: number;
  skip?: number;
}): Promise<GeoSearchResult> {
  const params = new URLSearchParams();

  if (options.query) params.append("q", sanitizeInput(options.query));
  if (options.city) params.append("city", options.city);
  if (options.state) params.append("state", options.state);
  if (options.lat) params.append("lat", options.lat.toString());
  if (options.lng) params.append("lng", options.lng.toString());
  if (options.radiusKm) params.append("radiusKm", options.radiusKm.toString());
  if (options.categoryId) params.append("category", options.categoryId);
  if (options.minPrice) params.append("minPrice", options.minPrice.toString());
  if (options.maxPrice) params.append("maxPrice", options.maxPrice.toString());
  if (options.inStock) params.append("inStock", "true");
  if (options.limit) params.append("limit", Math.min(options.limit, 50).toString());
  if (options.skip) params.append("skip", Math.max(options.skip, 0).toString());

  const response = await fetchAPI<GeoSearchResponse>(`/search/geo?${params.toString()}`);
  
  return {
    products: response.listings || [],
    total: response.total || 0,
    hasMore: response.hasMore || false,
    fallbackUsed: response.fallbackUsed,
    fallbackMessage: response.message,
    // Smart search fields
    didYouMean: response.didYouMean,
    correctedQuery: response.correctedQuery,
    originalQuery: response.originalQuery,
    autoCorreced: response.autoCorreced,
  };
}

// ==================== User API ====================

export const getUserProfile = (token: string): Promise<UserProfile> =>
  fetchWithAuth<UserProfile>('/users/me', token);

export const updateUserProfile = (token: string, data: Partial<UserProfile>) =>
  fetchWithAuth('/users/me', token, { 
    method: 'PUT', 
    body: sanitizeObject(data as Record<string, unknown>)
  });

// Register user with backend - LEGACY
export const registerUser = (token: string, data: {
  email: string;
  firebaseUid: string;
  businessName: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
}) => fetchWithAuth('/users/register', token, {
  method: 'POST',
  body: data,
});

// PHASE 2 - Complete profile after email verification
export interface ProfileCompleteData {
  role: 'buyer' | 'seller';
  businessName: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  gstNumber?: string;
  // NEW: Seller catalog fields
  enterpriseEstablishmentYear?: number;  // When company was founded (sellers only, editable once)
  sellerBannerImage?: string;  // Optional banner image for seller catalog
}

export interface ProfileCompleteResponse {
  message: string;
  user: UserProfile;
  isSeller: boolean;
  gstStatus: string | null;
}

export const completeProfile = (token: string, data: ProfileCompleteData): Promise<ProfileCompleteResponse> =>
  fetchWithAuth<ProfileCompleteResponse>('/auth/complete-profile', token, {
    method: 'POST',
    body: data,
  });

// NEW ARCHITECTURE: Check registration status
export interface CheckRegistrationResponse {
  profileComplete: boolean;
  isEmailVerified: boolean;
  needsVerification: boolean;
  needsProfileCompletion: boolean;
  user?: UserProfile;
  email?: string;
  firebaseUid?: string;
}

export const checkRegistrationStatus = (token: string): Promise<CheckRegistrationResponse> =>
  fetchWithAuth<CheckRegistrationResponse>('/auth/check-registration', token);

// NEW ARCHITECTURE: Cleanup for re-registration
export interface CleanupResponse {
  message: string;
  cleaned: boolean;
  email?: string;
}

export const cleanupForReregister = (email: string): Promise<CleanupResponse> =>
  fetchAPI<CleanupResponse>('/auth/cleanup-for-reregister', {
    method: 'POST',
    body: { email },
  });

// PHASE 7 - Get seller status
export interface SellerStatus {
  isSeller: boolean;
  gst: { number: string | null; status: string | null; verified: boolean };
  permissions: { canCreateDraft: boolean; canPublish: boolean };
  message: string;
}

export const getSellerStatus = (token: string): Promise<SellerStatus> =>
  fetchWithAuth<SellerStatus>('/seller/status', token);

export const deleteAccount = (token: string, reason: string = '') =>
  fetchWithAuth('/users/me/delete', token, {
    method: 'POST',
    body: { confirmation: true, reason: sanitizeInput(reason) },
  });

// ==================== Seller Catalog API ====================

export interface SellerCatalogResponse {
  seller: {
    id: string;
    slug: string;
    companyName: string;
    logo: string | null;
    bannerImage: string | null;
    location: {
      city: string;
      state: string;
      address: string;
    };
    phone: string;
    email: string;
    enterpriseEstablishmentYear: number | null;
    platformRegistrationYear: number | null;
    gstVerified: boolean;
    badgeType: string | null;
    rating: {
      avgRating: number;
      totalReviews: number;
      ratingDistribution: Record<number, number>;
    };
  };
  categories: Array<{
    categoryId: string;
    categoryName: string;
    categorySlug: string;
    categoryIcon: string;
    avgRating: number;
    totalReviews: number;
    totalProducts: number;
    products: Array<{
      listingId: string;
      productId: string;
      productName: string;
      productSlug: string;
      description: string;
      images: string[];
      pricingSlabs: Array<{minQty: number; maxQty: number; price: number}>;
      moq: number;
      avgRating: number;
      totalReviews: number;
      stockStatus: string;
    }>;
  }>;
  totalCategories: number;
  totalProducts: number;
}

export const getSellerCatalog = (
  slug: string, 
  productsPerCategory: number = 4
): Promise<SellerCatalogResponse> =>
  fetchAPI<SellerCatalogResponse>(
    `/seller-catalog/${slug}?products_per_category=${productsPerCategory}`
  );

export interface SellerCategoryProductsResponse {
  category: {
    id: string;
    name: string;
    slug: string;
    icon: string;
    avgRating: number;
    totalReviews: number;
  };
  products: Array<{
    listingId: string;
    productId: string;
    productName: string;
    productSlug: string;
    description: string;
    images: string[];
    pricingSlabs: Array<{minQty: number; maxQty: number; price: number}>;
    moq: number;
    avgRating: number;
    totalReviews: number;
    stockStatus: string;
  }>;
  pagination: {
    skip: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

export const getSellerCategoryProducts = (
  sellerSlug: string,
  categorySlug: string,
  skip: number = 0,
  limit: number = 20
): Promise<SellerCategoryProductsResponse> =>
  fetchAPI<SellerCategoryProductsResponse>(
    `/seller-catalog/${sellerSlug}/category/${categorySlug}?skip=${skip}&limit=${limit}`
  );

// ==================== Seller API ====================

export const getSellerStats = (token: string): Promise<SellerStats> =>
  fetchWithAuth<SellerStats>('/seller/stats', token);

export const getMyListings = (token: string): Promise<SellerListing[]> =>
  fetchWithAuth<{ listings: SellerListing[] }>('/seller/listings', token).then(res => res.listings || []);

export const createListing = (token: string, data: Record<string, unknown>) =>
  fetchWithAuth('/seller/listings', token, { method: 'POST', body: sanitizeObject(data) });

export const updateListing = (token: string, listingId: string, data: Record<string, unknown>) =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, { 
    method: 'PATCH', 
    body: sanitizeObject(data) 
  });

// Quick price update - alias for updateListing with price-specific data
export const quickPriceUpdate = (
  token: string, 
  listingId: string, 
  data: { pricingSlabs?: PricingSlab[]; basePrice?: number; validTill?: string; stockStatus?: string }
) => updateListing(token, listingId, data);

export const publishListing = (token: string, listingId: string) =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/publish`, token, { method: 'POST' });

export const deleteListing = (token: string, listingId: string) =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, { method: 'DELETE' });

// ==================== Enquiry API ====================

// REMOVED: Legacy enquiry endpoints
// Use standardized inquiry system instead:
// - createInquiry
// - getBuyerInquiries
// - getSellerInquiries
// - acceptInquiry
// - rejectInquiry
// - reportInquiry

// ==================== Admin API ====================

export const getAdminStats = (token: string): Promise<{ stats: AdminStats }> => 
  fetchWithAuth<{ stats: AdminStats }>('/admin/stats', token);

export const getAdminCategories = (token: string, includeInactive = false): Promise<{ categories: Category[] }> => 
  fetchWithAuth<{ categories: Category[] }>(`/admin/categories?includeInactive=${includeInactive}`, token);

export const createAdminCategory = (token: string, data: Record<string, unknown>) =>
  fetchWithAuth('/admin/categories', token, { method: 'POST', body: sanitizeObject(data) });

export const updateAdminCategory = (token: string, id: string, data: Record<string, unknown>) =>
  fetchWithAuth(`/admin/categories/${encodeURIComponent(id)}`, token, { 
    method: 'PATCH', 
    body: sanitizeObject(data) 
  });

export const deleteAdminCategory = (token: string, id: string, force = false) =>
  fetchWithAuth(`/admin/categories/${encodeURIComponent(id)}?force=${force}`, token, { method: 'DELETE' });

// Admin Users
export const getAdminUsers = (token: string, options?: { 
  search?: string; 
  status?: string; 
  isSeller?: boolean; 
  page?: number; 
  limit?: number 
}): Promise<{ users: AdminUser[]; total: number; pages: number }> => {
  const params = new URLSearchParams();
  if (options?.search) params.append('search', sanitizeInput(options.search));
  if (options?.status) params.append('status', options.status);
  if (options?.isSeller !== undefined) params.append('isSeller', options.isSeller.toString());
  if (options?.page) params.append('page', Math.max(1, options.page).toString());
  if (options?.limit) params.append('limit', Math.min(options.limit || 20, 100).toString());
  return fetchWithAuth<{ users: AdminUser[]; total: number; pages: number }>(`/admin/users?${params.toString()}`, token);
};

export const toggleAdminStatus = (token: string, userId: string) =>
  fetchWithAuth(`/admin/users/${encodeURIComponent(userId)}/toggle-admin`, token, { method: 'PATCH' });

export const restoreUser = (token: string, userId: string) =>
  fetchWithAuth(`/admin/users/${encodeURIComponent(userId)}/restore`, token, { method: 'POST' });

// Admin Products
export const getAdminProducts = (token: string, options?: {
  categoryId?: string;
  search?: string;
  includeInactive?: boolean;
  page?: number;
  limit?: number;
}): Promise<{ products: AdminProduct[]; total: number; pages: number }> => {
  const params = new URLSearchParams();
  if (options?.categoryId) params.append('categoryId', options.categoryId);
  if (options?.search) params.append('search', sanitizeInput(options.search));
  if (options?.includeInactive) params.append('includeInactive', 'true');
  if (options?.page) params.append('page', Math.max(1, options.page).toString());
  if (options?.limit) params.append('limit', Math.min(options.limit || 20, 100).toString());
  return fetchWithAuth<{ products: AdminProduct[]; total: number; pages: number }>(`/admin/products?${params.toString()}`, token);
};

export const createAdminProduct = (token: string, data: Record<string, unknown>) =>
  fetchWithAuth('/admin/products', token, { method: 'POST', body: sanitizeObject(data) });

export const updateAdminProduct = (token: string, id: string, data: Record<string, unknown>) =>
  fetchWithAuth(`/admin/products/${encodeURIComponent(id)}`, token, { method: 'PATCH', body: sanitizeObject(data) });

export const deleteAdminProduct = (token: string, id: string, force = false) =>
  fetchWithAuth(`/admin/products/${encodeURIComponent(id)}?force=${force}`, token, { method: 'DELETE' });

// Admin Spec Templates
export const getAdminSpecTemplates = (token: string, categoryId?: string, includeInactive = false): Promise<{ templates: AdminSpecTemplate[] }> => {
  const params = new URLSearchParams();
  params.append('includeInactive', includeInactive.toString());
  if (categoryId) params.append('categoryId', categoryId);
  return fetchWithAuth<{ templates: AdminSpecTemplate[] }>(`/admin/spec-templates?${params.toString()}`, token);
};

export const createAdminSpecTemplate = (token: string, data: Record<string, unknown>) =>
  fetchWithAuth('/admin/spec-templates', token, { method: 'POST', body: sanitizeObject(data) });

export const updateAdminSpecTemplate = (token: string, id: string, data: Record<string, unknown>) =>
  fetchWithAuth(`/admin/spec-templates/${encodeURIComponent(id)}`, token, { method: 'PATCH', body: sanitizeObject(data) });

export const deleteAdminSpecTemplate = (token: string, id: string, force = false) =>
  fetchWithAuth(`/admin/spec-templates/${encodeURIComponent(id)}?force=${force}`, token, { method: 'DELETE' });

// ==================== B2B Admin Foundation API ====================

export const getGlobalDropdowns = (
  token: string, 
  options?: { includeInactive?: boolean; includeSystem?: boolean }
): Promise<{ dropdowns: GlobalDropdown[]; total: number }> => {
  const params = new URLSearchParams();
  params.append('includeInactive', (options?.includeInactive ?? false).toString());
  params.append('includeSystem', (options?.includeSystem ?? true).toString());
  return fetchWithAuth<{ dropdowns: GlobalDropdown[]; total: number }>(
    `/admin/b2b/dropdowns?${params.toString()}`, 
    token
  );
};

export const getGlobalDropdown = (token: string, key: string): Promise<{ dropdown: GlobalDropdown }> =>
  fetchWithAuth<{ dropdown: GlobalDropdown }>(`/admin/b2b/dropdowns/${encodeURIComponent(key)}`, token);

export const createGlobalDropdown = (token: string, data: {
  key: string;
  name: string;
  description?: string;
  values: { value: string; label: string; displayOrder?: number }[];
}) => fetchWithAuth('/admin/b2b/dropdowns', token, { method: 'POST', body: data });

export const updateGlobalDropdown = (token: string, key: string, data: {
  name?: string;
  description?: string;
  values?: { value: string; label: string; displayOrder?: number; isActive?: boolean }[];
  isActive?: boolean;
}) => fetchWithAuth(`/admin/b2b/dropdowns/${encodeURIComponent(key)}`, token, { 
  method: 'PATCH', 
  body: data 
});

export const deleteGlobalDropdown = (token: string, key: string, force = false) =>
  fetchWithAuth(`/admin/b2b/dropdowns/${encodeURIComponent(key)}?force=${force}`, token, { 
    method: 'DELETE' 
  });

export const seedSystemDropdowns = (token: string) =>
  fetchWithAuth('/admin/b2b/seed-system-dropdowns', token, { method: 'POST' });

// B2B Categories
export const getB2BCategories = (
  token: string,
  includeInactive = false
): Promise<{ categories: B2BCategory[]; total: number }> =>
  fetchWithAuth<{ categories: B2BCategory[]; total: number }>(
    `/admin/b2b/categories?includeInactive=${includeInactive}`,
    token
  );

export const getB2BCategory = (
  token: string, 
  categoryId: string
): Promise<{ category: B2BCategory; specTemplates: AdminSpecTemplate[] }> =>
  fetchWithAuth<{ category: B2BCategory; specTemplates: AdminSpecTemplate[] }>(
    `/admin/b2b/categories/${encodeURIComponent(categoryId)}`,
    token
  );

export const createB2BCategory = (token: string, data: {
  name: string;
  description?: string;
  image?: string;
  icon?: string;
  displayOrder?: number;
  settings?: Partial<CategorySettings>;
}) => fetchWithAuth('/admin/b2b/categories', token, { method: 'POST', body: data });

export const updateB2BCategory = (token: string, categoryId: string, data: {
  name?: string;
  description?: string;
  image?: string;
  icon?: string;
  displayOrder?: number;
  settings?: Partial<CategorySettings>;
  isActive?: boolean;
}) => fetchWithAuth(`/admin/b2b/categories/${encodeURIComponent(categoryId)}`, token, { 
  method: 'PATCH', 
  body: data 
});

export const updateB2BCategorySettings = (token: string, categoryId: string, settings: CategorySettings) =>
  fetchWithAuth(`/admin/b2b/categories/${encodeURIComponent(categoryId)}/settings`, token, {
    method: 'PATCH',
    body: settings
  });

// B2B Spec Templates
export const getB2BSpecTemplates = (
  token: string,
  options?: { categoryId?: string; includeInactive?: boolean }
): Promise<{ templates: B2BSpecTemplate[]; total: number }> => {
  const params = new URLSearchParams();
  if (options?.categoryId) params.append('categoryId', options.categoryId);
  params.append('includeInactive', (options?.includeInactive ?? false).toString());
  return fetchWithAuth<{ templates: B2BSpecTemplate[]; total: number }>(
    `/admin/b2b/spec-templates?${params.toString()}`,
    token
  );
};

export const getB2BSpecTemplate = (
  token: string, 
  templateId: string
): Promise<{ template: B2BSpecTemplate }> =>
  fetchWithAuth<{ template: B2BSpecTemplate }>(
    `/admin/b2b/spec-templates/${encodeURIComponent(templateId)}`,
    token
  );

export const createB2BSpecTemplate = (token: string, data: {
  name: string;
  categoryId: string;
  description?: string;
  fields: Omit<SpecFieldDefinition, 'resolvedOptions' | 'resolvedValues'>[];
}) => fetchWithAuth('/admin/b2b/spec-templates', token, { method: 'POST', body: data });

export const updateB2BSpecTemplate = (token: string, templateId: string, data: {
  name?: string;
  description?: string;
  fields?: Omit<SpecFieldDefinition, 'resolvedOptions' | 'resolvedValues'>[];
  isActive?: boolean;
}) => fetchWithAuth(`/admin/b2b/spec-templates/${encodeURIComponent(templateId)}`, token, { 
  method: 'PATCH', 
  body: data 
});

export const deleteB2BSpecTemplate = (token: string, templateId: string, force = false) =>
  fetchWithAuth(`/admin/b2b/spec-templates/${encodeURIComponent(templateId)}?force=${force}`, token, { 
    method: 'DELETE' 
  });

// ==================== Seller Listing Management ====================

export const getSellerDashboard = (token: string): Promise<{
  stats: {
    total: number;
    draft: number;
    active: number;
    paused: number;
    archived: number;
  };
  recentListings: SellerListing[];
}> => fetchWithAuth('/seller/dashboard', token);

export const getSellerListings = (
  token: string,
  options?: {
    status?: string;
    categoryId?: string;
    page?: number;
    limit?: number;
  }
): Promise<{
  listings: SellerListing[];
  total: number;
  page: number;
  pages: number;
}> => {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.categoryId) params.append('categoryId', options.categoryId);
  if (options?.page) params.append('page', options.page.toString());
  if (options?.limit) params.append('limit', options.limit.toString());
  return fetchWithAuth(`/seller/listings?${params.toString()}`, token);
};

export const getSellerListing = (
  token: string,
  listingId: string
): Promise<{ listing: SellerListing; specTemplate?: B2BSpecTemplate | null }> =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token);

export interface ListingCreatePayload {
  productId: string;
  manufacturerId?: string;  // Phase 2: Dropdown selection (no free text)
  attributes: Record<string, string | number | boolean>;
  sellerRole: string;
  description?: string;
  images: string[];
  videos?: string[];  // Max 2 videos, 30 seconds each, 5MB each
  moq: number;
  stock: number;
  maxCapacity?: number;
  leadTime?: number;
  currency: string;
  pricingTiers: PricingTier[];
  datasheetUrl?: string;
  // Raw material pricing
  rate_per_kg?: number;
  material_supported?: string;
}

export const createSellerListing = (
  token: string, 
  data: ListingCreatePayload
): Promise<{ message: string; listing: SellerListing; variant?: unknown }> =>
  fetchWithAuth('/seller/listings', token, { method: 'POST', body: data });

export interface ListingUpdatePayload {
  description?: string;
  images?: string[];
  videos?: string[];  // Max 2 videos
  status?: 'draft' | 'active' | 'paused' | 'archived';
  moq?: number;
  stock?: number;
  maxCapacity?: number;
  leadTime?: number;
  datasheetUrl?: string;
  attributes?: Record<string, string | number | boolean>;  // Creates new variant if changed
  // Raw material pricing
  rate_per_kg?: number;
  material_supported?: string;
}

export const updateSellerListing = (token: string, listingId: string, data: ListingUpdatePayload): Promise<{ 
  message: string; 
  listing: SellerListing; 
  variantChanged?: boolean;
  newVariant?: unknown;
}> =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, { 
    method: 'PATCH', 
    body: data 
  });

export const getProductById = (productId: string): Promise<Product> =>
  fetchAPI<Product>(`/products/${encodeURIComponent(productId)}`);

// REMOVED: getSpecTemplateById - Use getCategorySpecTemplate instead (category-based architecture)

// Pricing Updates
export interface PricingUpdatePayload {
  pricingTiers: PricingTier[];
}

export const updateSellerPricing = (token: string, listingId: string, data: PricingUpdatePayload): Promise<{ 
  message: string; 
  pricingTiers: PricingTier[]; 
  lastUpdated: string 
}> =>
  fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/pricing`, token, {
    method: 'PATCH',
    body: data
  });

// Listing Actions
export const publishSellerListing = (token: string, listingId: string): Promise<{
  message: string;
  status: string;
  publishedAt: string;
}> => fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/publish`, token, { 
  method: 'POST' 
});

export const pauseSellerListing = (token: string, listingId: string): Promise<{
  message: string;
  status: string;
}> => fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/pause`, token, { 
  method: 'POST' 
});

export const deleteSellerListing = (token: string, listingId: string, hardDelete = false): Promise<{
  message: string;
}> => fetchWithAuth(
  `/seller/listings/${encodeURIComponent(listingId)}?hardDelete=${hardDelete}`, 
  token, 
  { method: 'DELETE' }
);

// Seller Subscription
export const getSellerSubscription = (token: string): Promise<SellerSubscriptionStatus> =>
  fetchWithAuth('/seller/subscription/status', token);

export const getSellerSubscriptionStatus = (token: string): Promise<SellerSubscriptionStatus> =>
  fetchWithAuth('/seller/subscription/status', token);

// ==================== Admin Inquiries ====================

export const getAdminInquiries = (
  token: string,
  options?: {
    status?: string;
    sellerId?: string;
    buyerId?: string;
    category?: string;
    dateFrom?: string;
    dateTo?: string;
    page?: number;
    limit?: number;
  }
): Promise<{
  inquiries: AdminInquiry[];
  total: number;
  page: number;
  pages: number;
}> => {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.sellerId) params.append('sellerId', options.sellerId);
  if (options?.buyerId) params.append('buyerId', options.buyerId);
  if (options?.category) params.append('category', options.category);
  if (options?.dateFrom) params.append('dateFrom', options.dateFrom);
  if (options?.dateTo) params.append('dateTo', options.dateTo);
  if (options?.page) params.append('page', String(options.page));
  if (options?.limit) params.append('limit', String(options.limit));
  return fetchWithAuth(`/admin/inquiries?${params.toString()}`, token);
};

export const getAdminAnalytics = (
  token: string,
  days: number = 30
): Promise<AdminAnalytics> =>
  fetchWithAuth(`/admin/analytics?days=${days}`, token);

export const getAdminKPIMetrics = (token: string): Promise<AdminKPIMetrics> =>
  fetchWithAuth('/admin/kpi-metrics', token);

// ==================== Subscription Management API ====================

export interface SubscriptionWithUser {
  subscription: SubscriptionDetails;
  user: {
    id: string;
    businessName: string;
    email: string;
    isSeller: boolean;
  };
}

export const getAdminSubscription = (
  token: string,
  userId: string
): Promise<SubscriptionWithUser> =>
  fetchWithAuth(`/admin/subscriptions/manage/${userId}`, token);

export const activateSubscription = (
  token: string,
  userId: string,
  data: {
    planName: 'free' | 'trial' | 'pro';
    startDate: string;
    durationDays?: number;
    notes?: string;
  }
): Promise<{ message: string; subscription: SubscriptionDetails }> =>
  fetchWithAuth(`/admin/subscriptions/activate/${userId}`, token, {
    method: 'POST',
    body: data,
  });

export const extendSubscription = (
  token: string,
  userId: string,
  data: { extendDays: number; notes?: string }
): Promise<{ message: string; subscription: unknown }> =>
  fetchWithAuth(`/admin/subscriptions/extend/${userId}`, token, {
    method: 'POST',
    body: data,
  });

export const suspendSubscription = (
  token: string,
  userId: string,
  reason: string
): Promise<{ message: string; subscription: unknown }> =>
  fetchWithAuth(`/admin/subscriptions/suspend/${userId}`, token, {
    method: 'POST',
    body: { reason },
  });

export const reactivateSubscription = (
  token: string,
  userId: string
): Promise<{ message: string; subscription: unknown }> =>
  fetchWithAuth(`/admin/subscriptions/reactivate/${userId}`, token, {
    method: 'POST',
  });

export const runExpiryCheck = (
  token: string
): Promise<{ message: string; expiredCount: number; checkedAt: string }> =>
  fetchWithAuth('/admin/subscriptions/run-expiry-check', token, {
    method: 'POST',
  });

export const getExpiringSubscriptions = (
  token: string,
  days: number = 10
): Promise<{ expiringWithinDays: number; count: number; subscriptions: unknown[] }> =>
  fetchWithAuth(`/admin/subscriptions/expiring?days=${days}`, token);

// Admin Inquiries CSV Export
export const exportAdminInquiries = async (
  token: string,
  options?: {
    status?: string;
    sellerId?: string;
    buyerId?: string;
    dateFrom?: string;
    dateTo?: string;
  }
): Promise<Blob> => {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.sellerId) params.append('sellerId', options.sellerId);
  if (options?.buyerId) params.append('buyerId', options.buyerId);
  if (options?.dateFrom) params.append('dateFrom', options.dateFrom);
  if (options?.dateTo) params.append('dateTo', options.dateTo);
  
  const sanitizedEndpoint = `/api/admin/inquiries/export?${params.toString()}`;
  const url = `${API_URL}${sanitizedEndpoint}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'text/csv',
    },
  });

  if (!response.ok) {
    throw new ApiError('Failed to export inquiries', response.status);
  }

  return response.blob();
};

// ==================== Email Verification API ====================

/**
 * Send verification email via backend (Resend)
 * Uses auth token - backend gets user email from the token.
 * 
 * MIGRATION: Now uses Resend instead of Zoho SMTP.
 */
export const sendVerificationEmail = (token: string): Promise<{
  success: boolean;
  message: string;
}> => fetchWithAuth('/send-verification', token, {
  method: 'POST',
});

/**
 * Verify email token from verification link
 * 
 * MIGRATION: Token is now SHA256 hashed before verification.
 */
export const verifyEmailToken = (token: string): Promise<{
  success: boolean;
  message: string;
  redirectUrl?: string;
}> => fetchAPI(`/verify-email?token=${encodeURIComponent(token)}`);

/**
 * Resend verification email via backend (Resend)
 * Uses auth token - backend gets user email from the token.
 * Rate limited to prevent abuse.
 * 
 * MIGRATION: Now uses Resend instead of Zoho SMTP.
 */
export const resendVerificationEmail = (token: string): Promise<{
  success: boolean;
  message: string;
}> => fetchWithAuth('/resend-verification', token, {
  method: 'POST',
});

// ==================== OTP-Based Registration ====================

/**
 * Request OTP for registration verification
 * 
 * This replaces the email verification link system.
 * OTP is sent to the user's email address.
 * 
 * Security:
 * - Rate limited: 5 requests per minute
 * - Max 5 OTP requests per email per hour
 * - 30-second cooldown between requests
 */
export interface OTPRequestResponse {
  success: boolean;
  message: string;
  expires_at?: string;
  cooldown_until?: string;
  error_code?: string;
  cooldown_remaining?: number;
  _mock?: boolean;
  _otp?: string; // Only in mock mode for testing
}

export const requestRegistrationOTP = (
  email: string,
  name?: string
): Promise<OTPRequestResponse> => 
  fetchAPI<OTPRequestResponse>('/auth/register/request-otp', {
    method: 'POST',
    body: { email: email.toLowerCase().trim(), name },
  });

/**
 * Verify OTP for registration
 * 
 * This verifies the 6-digit OTP entered by the user.
 * After successful verification, proceed with Firebase signup.
 * 
 * Security:
 * - Rate limited: 10 requests per minute
 * - Max 5 verification attempts per OTP
 * - OTP expires after 10 minutes
 */
export interface OTPVerifyResponse {
  success: boolean;
  message: string;
  verified?: boolean;
  email?: string;
  error_code?: string;
  attempts_remaining?: number;
}

export const verifyRegistrationOTP = (
  email: string,
  otp: string
): Promise<OTPVerifyResponse> =>
  fetchAPI<OTPVerifyResponse>('/auth/register/verify-otp', {
    method: 'POST',
    body: { email: email.toLowerCase().trim(), otp: otp.trim() },
  });

/**
 * Check OTP verification status for an email
 * 
 * Used to check if user has already verified OTP.
 * Helpful when user refreshes the page during registration.
 */
export interface OTPStatusResponse {
  verified: boolean;
  message: string;
}

export const checkOTPStatus = (email: string): Promise<OTPStatusResponse> =>
  fetchAPI<OTPStatusResponse>(`/auth/register/otp-status?email=${encodeURIComponent(email.toLowerCase().trim())}`);

// Category Spec Template
export const getCategorySpecTemplate = (
  token: string,
  categoryId: string
): Promise<{
  category: {
    _id: string;
    name: string;
    settings: CategorySettings;
  };
  specTemplate: B2BSpecTemplate | null;
  note?: string;
}> => fetchWithAuth(`/seller/categories/${encodeURIComponent(categoryId)}/spec-template`, token);

// NEW: Get spec template directly from product's specTemplateIds (more reliable)
export const getProductSpecTemplate = (
  token: string,
  productId: string
): Promise<{
  product: {
    _id: string;
    name: string;
    categoryId: string | null;
    specTemplateIds: string[];
  };
  specTemplates: B2BSpecTemplate[];  // All available templates
  specTemplate: B2BSpecTemplate | null;  // First/default template (backward compatible)
  note?: string;
}> => fetchWithAuth(`/seller/products/${encodeURIComponent(productId)}/spec-template`, token);

// ==================== Image Upload ====================

const ALLOWED_IMAGE_TYPES = [
  'image/jpeg', 
  'image/jpg',
  'image/png', 
  'image/webp',
  'image/heic',
  'image/heif',
];
const MAX_CATEGORY_IMAGE_SIZE = 1 * 1024 * 1024;
const MAX_PRODUCT_IMAGE_SIZE = 5 * 1024 * 1024;  // 5MB per image (per spec)
const MAX_PRODUCT_IMAGES = 5;  // Max 5 images per listing

function validateImageFile(file: File, maxSize: number, context: string): void {
  const fileType = file.type.toLowerCase();
  const fileName = file.name.toLowerCase();
  
  const isValidType = ALLOWED_IMAGE_TYPES.includes(fileType) ||
    fileName.endsWith('.jpg') ||
    fileName.endsWith('.jpeg') ||
    fileName.endsWith('.png') ||
    fileName.endsWith('.webp') ||
    fileName.endsWith('.heic') ||
    fileName.endsWith('.heif');
    
  if (!isValidType) {
    throw new ApiError(
      `Invalid image type for ${context}. Allowed: JPEG, PNG, WEBP`,
      400,
      'INVALID_IMAGE_TYPE'
    );
  }
  if (file.size > maxSize) {
    const maxMB = (maxSize / (1024 * 1024)).toFixed(1);
    throw new ApiError(
      `Image too large. Maximum size: ${maxMB} MB`,
      400,
      'IMAGE_TOO_LARGE'
    );
  }
}

export async function uploadCategoryImage(token: string, file: File): Promise<{ imageUrl: string }> {
  validateImageFile(file, MAX_CATEGORY_IMAGE_SIZE, 'category');
  const { uploadAdminCategoryImage } = await import('./cloudinary');
  const result = await uploadAdminCategoryImage(file);
  return { imageUrl: result.url };
}

export async function uploadProductImages(token: string, files: File[]): Promise<{ images: string[] }> {
  if (files.length === 0) {
    throw new ApiError('At least one image is required', 400);
  }
  if (files.length > MAX_PRODUCT_IMAGES) {
    throw new ApiError(`Maximum ${MAX_PRODUCT_IMAGES} images allowed`, 400);
  }
  
  files.forEach((file, idx) => {
    validateImageFile(file, MAX_PRODUCT_IMAGE_SIZE, `product image ${idx + 1}`);
  });
  
  const { uploadSellerProductImage } = await import('./cloudinary');
  const uploadPromises = files.map(file => uploadSellerProductImage(file));
  const results = await Promise.all(uploadPromises);
  
  return { images: results.map(r => r.url) };
}

// Video upload constants
const MAX_PRODUCT_VIDEOS = 2;
const MAX_VIDEO_SIZE = 5 * 1024 * 1024; // 5MB
const MAX_VIDEO_DURATION = 30; // seconds

export async function uploadProductVideos(token: string, files: File[]): Promise<{ videos: string[] }> {
  if (files.length === 0) {
    throw new ApiError('At least one video is required', 400);
  }
  if (files.length > MAX_PRODUCT_VIDEOS) {
    throw new ApiError(`Maximum ${MAX_PRODUCT_VIDEOS} videos allowed`, 400);
  }
  
  // Validate each video file
  files.forEach((file, idx) => {
    // Check MIME type
    if (!file.type.startsWith('video/')) {
      throw new ApiError(`File ${idx + 1} is not a valid video`, 400, 'INVALID_FILE_TYPE');
    }
    
    // Check file size
    if (file.size > MAX_VIDEO_SIZE) {
      throw new ApiError(`Video ${idx + 1} exceeds maximum size of 5MB`, 400, 'FILE_TOO_LARGE');
    }
  });
  
  const { uploadSellerProductVideo } = await import('./cloudinary');
  const uploadPromises = files.map(file => uploadSellerProductVideo(file));
  const results = await Promise.all(uploadPromises);
  
  return { videos: results.map(r => r.url) };
}

export async function uploadProductDatasheet(token: string, file: File): Promise<{ url: string }> {
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    throw new ApiError('Only PDF files are allowed for datasheets', 400, 'INVALID_FILE_TYPE');
  }
  
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    throw new ApiError('Datasheet file must be less than 5MB', 400, 'FILE_TOO_LARGE');
  }
  
  const { uploadSellerDatasheet } = await import('./cloudinary');
  const result = await uploadSellerDatasheet(file);
  return { url: result.url };
}

// ==================== Seller Requests ====================

export interface ManufacturerRequestCreate {
  brandName: string;
  legalName?: string;
  website?: string;
  country?: string;
  reason?: string;
  supportingDocuments?: string[];
}

export interface ProductRequestCreate {
  productName: string;
  suggestedCategoryId: string;
  manufacturerId?: string;
  description?: string;
  reason?: string;
}

export interface CategoryRequestCreate {
  categoryName: string;
  description?: string;
  reason?: string;
}

export interface SpecFieldRequestCreate {
  categoryId: string;
  fieldName: string;
  fieldType?: 'text' | 'number' | 'dropdown' | 'boolean';
  suggestedOptions?: string[];
  unit?: string;
  reason?: string;
}

export const requestManufacturer = (
  token: string,
  data: ManufacturerRequestCreate
): Promise<{ message: string; request: SellerRequest }> =>
  fetchWithAuth('/seller/requests/manufacturer', token, { method: 'POST', body: data });

export const getMyManufacturerRequests = (
  token: string,
  status?: string
): Promise<{ requests: SellerRequest[] }> =>
  fetchWithAuth(`/seller/requests/manufacturer${status ? `?status=${status}` : ''}`, token);

export const requestProduct = (
  token: string,
  data: ProductRequestCreate
): Promise<{ message: string; request: SellerRequest }> =>
  fetchWithAuth('/seller/requests/product', token, { 
    method: 'POST', 
    body: {
      productName: data.productName,
      suggestedCategoryId: data.suggestedCategoryId,
      manufacturerId: data.manufacturerId,
      description: data.description,
      reason: data.reason
    }
  });

export const getMyProductRequests = (
  token: string,
  status?: string
): Promise<{ requests: SellerRequest[] }> =>
  fetchWithAuth(`/seller/requests/product${status ? `?status=${status}` : ''}`, token);

export const requestCategory = (
  token: string,
  data: CategoryRequestCreate
): Promise<{ message: string; request: SellerRequest }> =>
  fetchWithAuth('/seller/requests/category', token, { 
    method: 'POST', 
    body: {
      categoryName: data.categoryName,
      description: data.description,
      reason: data.reason
    }
  });

export const getMyCategoryRequests = (
  token: string,
  status?: string
): Promise<{ requests: SellerRequest[] }> =>
  fetchWithAuth(`/seller/requests/category${status ? `?status=${status}` : ''}`, token);

export const requestSpecField = (
  token: string,
  data: SpecFieldRequestCreate
): Promise<{ message: string; request: SellerRequest }> =>
  fetchWithAuth('/seller/requests/spec-field', token, { 
    method: 'POST', 
    body: {
      categoryId: data.categoryId,
      fieldName: data.fieldName,
      fieldType: data.fieldType,
      suggestedOptions: data.suggestedOptions,
      unit: data.unit,
      reason: data.reason
    }
  });

export const getMySpecFieldRequests = (
  token: string,
  status?: string
): Promise<{ requests: SellerRequest[] }> =>
  fetchWithAuth(`/seller/requests/spec-field${status ? `?status=${status}` : ''}`, token);

// ==================== Public Products & Manufacturers ====================

export const getProductsByCategory = (
  categoryId: string
): Promise<AdminProduct[]> =>
  fetchBase(`/products/by-category/${encodeURIComponent(categoryId)}`);

export const getManufacturers = (
  categoryId?: string,
  search?: string
): Promise<{ manufacturers: Manufacturer[] }> => {
  const params = new URLSearchParams();
  if (categoryId) params.append('categoryId', categoryId);
  if (search) params.append('search', search);
  return fetchBase(`/manufacturers?${params.toString()}`);
};

// ==================== Standardized Inquiry System ====================

// Create inquiry (standardized endpoint)
// SSOT: All fields use camelCase
export const createInquiry = (
  token: string,
  data: {
    productId?: string;
    sellerId: string;
    listingId?: string;
    quantity: number;
    message?: string;
    buyerType?: 'trader' | 'contractor' | 'oem' | 'manufacturer' | 'other';
    calculationData?: {
      // Legacy fields
      material?: string;
      shape?: string;
      dimensions?: Record<string, string>;
      quantity?: number;
      weight_per_piece?: number;
      total_weight?: number;
      rate_per_kg?: number;
      calculated_price?: number;
      // New dynamic calculator fields
      calculator_name?: string;
      material_name?: string;
      formula_used?: string;
      formula_description?: string;
      field_summary?: Record<string, string>;
      output_unit?: string;
    };
  }
): Promise<{
  success: boolean;
  message: string;
  inquiryId: string;
  status: string;
  productName?: string;
  sellerName?: string;
  whatsapp?: {
    enabled: boolean;
    phoneNumber: string;
    label?: string | null;
    sellerName?: string;
  } | null;
}> => fetchWithAuth('/inquiries', token, {
  method: 'POST',
  body: {
    productId: data.productId,
    sellerId: data.sellerId,
    listingId: data.listingId,
    quantity: data.quantity,
    message: data.message,
    buyerType: data.buyerType,
    calculationData: data.calculationData,
  }
});

// Get buyer inquiries
export const getBuyerInquiries = (
  token: string,
  options?: { status?: string; page?: number; limit?: number }
): Promise<{
  inquiries: BuyerInquiry[];
  total: number;
  page: number;
  pages: number;
}> => {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.page) params.append('page', String(options.page));
  if (options?.limit) params.append('limit', String(options.limit));
  return fetchWithAuth(`/buyer/inquiries?${params.toString()}`, token);
};

// Get seller inquiries
export const getSellerInquiries = (
  token: string,
  options?: { status?: string; page?: number; limit?: number }
): Promise<SellerInquiriesResponse> => {
  const params = new URLSearchParams();
  if (options?.status) params.append('status', options.status);
  if (options?.page) params.append('page', String(options.page));
  if (options?.limit) params.append('limit', String(options.limit));
  return fetchWithAuth(`/seller/inquiries?${params.toString()}`, token);
};

// Accept inquiry with quote
export const acceptInquiry = (
  token: string,
  inquiryId: string,
  data: {
    quotedPrice: number;
    moq?: number;
    leadTimeDays?: number;
    validityDays?: number;
    sellerNote?: string;
  }
): Promise<{
  success: boolean;
  message: string;
  inquiryId: string;
  whatsappLink?: string | null;
  buyerContact: {
    name?: string;
    phone?: string;
    email?: string;
    company?: string;
  };
  sellerContact?: {
    businessName?: string;
  };
  // SSOT: Quote data from QuotationService
  quote: {
    quoteId?: string;
    unitPrice: number;
    moq?: number;
    leadTimeDays?: number;
    validityDate?: string;
    validityDays?: number;
    totalPrice?: number;
    productName?: string;
    sellerName?: string;
    buyerName?: string;
    status?: string;
  };
  subscriptionUsage: {
    used: number;
    limit: number;
    remaining: number;
    isUnlimited?: boolean;
  };
}> => fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/accept`, token, {
  method: 'POST',
  body: data
});

// Reject inquiry
export const rejectInquiry = (
  token: string,
  inquiryId: string,
  data: {
    reason: 'price_too_low' | 'not_available' | 'moq_issue' | 'location_not_serviceable' | 'capacity_full' | 'other';
    note?: string;
  }
): Promise<{
  message: string;
  inquiryId: string;
  reason: string;
}> => fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/reject`, token, {
  method: 'POST',
  body: data
});

// Report inquiry
export const reportInquiry = (
  token: string,
  inquiryId: string,
  data: {
    reportType: 'spam' | 'unrealistic_quantity' | 'fake_inquiry' | 'abusive' | 'other';
    details?: string;
  }
): Promise<{
  message: string;
  inquiryId: string;
  reportType: string;
}> => fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/report`, token, {
  method: 'POST',
  body: data
});

// ==================== ENTERPRISE PRODUCT ENDPOINTS ====================

export interface EnterpriseProductSeller {
  listingId: string;
  sellerId: string;
  variantId?: string;
  companyName: string;
  location: string;
  city?: string;
  state?: string;
  sellerRole: string;
  sellerSlug?: string;  // Seller catalog page slug
  badgeType?: 'none' | 'choice' | 'trusted';  // UdyogConnect seller badge
  searchableAttributes: Record<string, string | number>;
  attributeLabels: Record<string, string>;
  pricingTiers: PricingTier[];
  lowestPrice?: number;
  moq: number;
  stock: number;
  leadTimeDays?: number;
  images: string[];
  videos?: string[];  // Product demo videos (max 2, 30s each)
  stockStatus: 'in_stock' | 'out_of_stock' | 'limited';
  // Ranking fields (populated when sortBy=ranking)
  rankingScore?: number;
  rankingBreakdown?: RankingBreakdown;
  // Rating aggregation (stored in sellerListing for performance)
  avgRating?: number;
  totalReviews?: number;
}

export interface EnterpriseProductResponse {
  product: {
    _id: string;
    name: string;
    slug?: string;
    description?: string;
    images: string[];
    categoryId?: string;
    categoryName?: string;
    product_type?: 'raw_material' | 'standard_product';
  };
  specTemplate?: {
    templateId: string;
    name: string;
    fields: Array<{
      key: string;
      label: string;
      fieldType: string;
      unit?: string;
      filterable?: boolean;
      options?: string[];
    }>;
    version: number;
  };
  summary: {
    sellerCount: number;
    minPrice?: number;
    variantCount: number;
    totalPages: number;
  };
  availableFacets: Record<string, (string | number)[]>;
  sellers: EnterpriseProductSeller[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
  // Token-based slug resolution redirect info
  redirect?: {
    needed: boolean;
    canonicalSlug: string;
    canonicalUrl: string;
  };
}

export interface ProductFacetsResponse {
  productId: string;
  facets: Record<string, {
    values: (string | number)[];
    count: number;
    metadata: {
      label: string;
      fieldType: string;
      unit?: string;
      filterable?: boolean;
      options?: string[];
    };
  }>;
  totalListings: number;
  specTemplate?: string;
}

export interface FilterRequest {
  attributes?: Record<string, unknown>;
  sortBy?: 'price' | 'leadTime' | 'stock' | 'updatedAt' | 'ranking';
  order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
  // Buyer context for location-based ranking
  buyerCity?: string;
  buyerState?: string;
  // Debug mode for ranking breakdown
  debug?: boolean;
}

export interface RankingBreakdown {
  listing_id: string;
  raw_score: number;
  normalized_score: number;
  components: Record<string, number>;
  factors: Record<string, unknown>;
}

export interface FilterResponse {
  results: EnterpriseProductSeller[];
  total: number;
  page: number;
  pages: number;
  fallbackLevel: number;
  fallbackMessage?: string;
  appliedFilters: Record<string, unknown>;
  sortedBy?: string;
}

// Get enterprise product page data (single aggregation)
export const getEnterpriseProduct = (
  productId: string,
  page: number = 1,
  limit: number = 20
): Promise<EnterpriseProductResponse> =>
  fetchAPI(`/products/${encodeURIComponent(productId)}/enterprise?page=${page}&limit=${limit}`);

// Get product facets for filtering
export const getProductFacets = (productId: string): Promise<ProductFacetsResponse> =>
  fetchAPI(`/products/${encodeURIComponent(productId)}/facets`);

// Filter product listings with fallback
export const filterProductListings = (
  productId: string,
  filters: FilterRequest
): Promise<FilterResponse> =>
  fetchAPI(`/products/${encodeURIComponent(productId)}/filter`, {
    method: 'POST',
    body: filters  // fetchAPI handles JSON.stringify internally
  });

// ==========================================
// QUOTE API ENDPOINTS (Hybrid RFQ System)
// ==========================================

export interface Quote {
  quoteId: string;
  inquiryId: string;
  productId: string;
  productName: string;
  sellerId: string;
  sellerName: string;
  buyerId: string;
  buyerName: string;
  buyerCompany?: string;
  requestedQuantity: number;
  unitPrice: number;
  moq: number;
  packagingCharges: number;
  transportIncluded: boolean;
  totalPrice: number;
  leadTimeDays: number;
  validityDate: string;
  validityDays: number;
  terms?: string;
  customMessage?: string;
  status: 'sent' | 'viewed' | 'accepted' | 'rejected' | 'expired';
  whatsappRedirectUsed: boolean;
  createdAt: string;
  viewedAt?: string;
  acceptedAt?: string;
  rejectedAt?: string;
  rejectionReason?: string;
}

export interface CreateQuoteRequest {
  inquiryId: string;
  unitPrice: number;
  moq: number;
  leadTimeDays: number;
  validityDays?: number;
  packagingCharges?: number;
  terms?: string;
  customMessage?: string;
}

export interface QuoteResponse {
  success: boolean;
  quote: Quote;
  accessToken: string;
}

export interface WhatsAppRedirectResponse {
  message: string;
  secureUrl: string;
  quoteId: string;
  whatsappLink: string | null;
  buyerPhoneAvailable: boolean;
}

export interface QuoteAcceptResponse {
  success: boolean;
  message: string;
  quoteId: string;
  sellerContact: {
    name?: string;
    phone?: string;
    email?: string;
    whatsapp?: string;
  };
}

export interface QuoteListResponse {
  quotes: Quote[];
  total: number;
  page: number;
  pages: number;
}

// Create a quote (seller)
export const createQuote = (
  token: string,
  data: CreateQuoteRequest
): Promise<QuoteResponse> =>
  fetchWithAuth('/quotes/create', token, {
    method: 'POST',
    body: data
  });

// Get WhatsApp redirect link (seller)
export const getWhatsAppRedirect = (
  token: string,
  quoteId: string
): Promise<WhatsAppRedirectResponse> =>
  fetchWithAuth(`/quotes/${encodeURIComponent(quoteId)}/whatsapp-redirect`, token, {
    method: 'POST'
  });

// View quote (buyer)
export const viewQuote = (
  token: string,
  quoteId: string,
  accessToken?: string
): Promise<{ quote: Quote; canAccept: boolean; isExpired: boolean; paymentComingSoon: boolean }> => {
  const params = accessToken ? `?token=${encodeURIComponent(accessToken)}` : '';
  return fetchWithAuth(`/quotes/${encodeURIComponent(quoteId)}${params}`, token);
};

// View quote (public with token)
export const viewQuotePublic = (
  quoteId: string,
  accessToken: string
): Promise<{ quote: Partial<Quote>; isExpired: boolean; requiresLogin: boolean; paymentComingSoon: boolean }> =>
  fetchAPI(`/quotes/public/${encodeURIComponent(quoteId)}?token=${encodeURIComponent(accessToken)}`);

// Accept quote (buyer)
export const acceptQuote = (
  token: string,
  quoteId: string
): Promise<QuoteAcceptResponse> =>
  fetchWithAuth(`/quotes/${encodeURIComponent(quoteId)}/accept`, token, {
    method: 'POST'
  });

// Reject quote (buyer)
export const rejectQuote = (
  token: string,
  quoteId: string,
  reason?: string
): Promise<{ success: boolean; message: string; quoteId: string }> =>
  fetchWithAuth(`/quotes/${encodeURIComponent(quoteId)}/reject`, token, {
    method: 'POST',
    body: { reason }
  });

// Get seller's quotes
export const getSellerQuotes = (
  token: string,
  params?: { status?: string; page?: number; limit?: number }
): Promise<QuoteListResponse> => {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
  return fetchWithAuth(`/quotes/seller${query}`, token);
};

// Get buyer's quotes
export const getBuyerQuotes = (
  token: string,
  params?: { status?: string; page?: number; limit?: number }
): Promise<QuoteListResponse> => {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
  return fetchWithAuth(`/quotes/buyer${query}`, token);
};

// Get quote analytics (seller)
export const getQuoteAnalytics = (
  token: string,
  days: number = 30
): Promise<{
  period: string;
  totalQuotes: number;
  viewRate: number;
  acceptanceRate: number;
  rejectionRate: number;
  expiryRate: number;
  totalValue: number;
  acceptedValue: number;
}> =>
  fetchWithAuth(`/quotes/analytics?days=${days}`, token);

// ==================== SELLER WHATSAPP CONTACTS ====================

export interface WhatsAppContact {
  id: string;
  phoneNumber: string;
  label: string | null;
  isPrimary: boolean;
  createdAt: string;
}

export interface WhatsAppSettings {
  autoWhatsappConnect: boolean;
  primaryContact: WhatsAppContact | null;
}

// Get seller's WhatsApp contacts
export const getWhatsAppContacts = (token: string): Promise<{
  contacts: WhatsAppContact[];
}> => fetchWithAuth('/seller/whatsapp/contacts', token);

// Add WhatsApp contact
export const addWhatsAppContact = (
  token: string,
  data: { phoneNumber: string; label?: string; isPrimary?: boolean }
): Promise<{
  success: boolean;
  message: string;
  contact: WhatsAppContact;
}> => fetchWithAuth('/seller/whatsapp/contacts', token, {
  method: 'POST',
  body: data
});

// Update WhatsApp contact
export const updateWhatsAppContact = (
  token: string,
  contactId: string,
  data: { phoneNumber?: string; label?: string; isPrimary?: boolean }
): Promise<{
  success: boolean;
  message: string;
  contact: WhatsAppContact;
}> => fetchWithAuth(`/seller/whatsapp/contacts/${contactId}`, token, {
  method: 'PATCH',
  body: data
});

// Delete WhatsApp contact
export const deleteWhatsAppContact = (
  token: string,
  contactId: string
): Promise<{ success: boolean; message: string }> =>
  fetchWithAuth(`/seller/whatsapp/contacts/${contactId}`, token, {
    method: 'DELETE'
  });

// Set contact as primary
export const setWhatsAppPrimaryContact = (
  token: string,
  contactId: string
): Promise<{ success: boolean; message: string }> =>
  fetchWithAuth(`/seller/whatsapp/contacts/${contactId}/set-primary`, token, {
    method: 'POST'
  });

// Get WhatsApp settings
export const getWhatsAppSettings = (token: string): Promise<WhatsAppSettings> =>
  fetchWithAuth('/seller/whatsapp/settings', token);

// Update WhatsApp settings
export const updateWhatsAppSettings = (
  token: string,
  data: { autoWhatsappConnect: boolean }
): Promise<{
  success: boolean;
  message: string;
  autoWhatsappConnect: boolean;
}> => fetchWithAuth('/seller/whatsapp/settings', token, {
  method: 'PATCH',
  body: data
});

// Get seller's primary contact (public - for buyer inquiry flow)
export const getSellerPrimaryWhatsApp = (sellerId: string): Promise<{
  contact: { phoneNumber: string; label: string | null } | null;
  autoConnect: boolean;
}> => fetchAPI(`/seller/whatsapp/seller/${sellerId}/primary`);

// Re-export ApiError for consumers
export { ApiError };
