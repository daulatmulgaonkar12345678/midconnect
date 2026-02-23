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

// API Configuration - uses environment variable only
const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL && typeof window !== 'undefined') {
  console.warn('NEXT_PUBLIC_API_URL not configured. API calls will fail.');
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
  
  const healthUrl = `${API_URL}/health`;
  
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

  const sanitizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
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

export const getCategories = (): Promise<Category[]> => 
  fetchAPI<Category[]>('/categories/all');

export const getPublicCategories = (): Promise<{
  _id: string;
  name: string;
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
  products: ProductWithSellers[];
  total: number;
  guidanceDisclaimer?: string;
}

export const searchProducts = (
  query: string,
  options: { categoryId?: string; limit?: number; skip?: number } = {}
): Promise<SearchResult> => {
  const sanitizedQuery = sanitizeInput(query);
  return fetchAPI<SearchResult>('/search/products', {
    method: 'POST',
    body: {
      query: sanitizedQuery,
      categoryId: options.categoryId ? encodeURIComponent(options.categoryId) : undefined,
      limit: Math.min(options.limit || 50, 100),
      skip: Math.max(options.skip || 0, 0),
    },
  });
};

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
  attributes: Record<string, string | number | boolean>;
  sellerRole: string;
  description?: string;
  images: string[];
  moq: number;
  stock: number;
  maxCapacity?: number;
  leadTime?: number;
  currency: string;
  pricingTiers: PricingTier[];
  datasheetUrl?: string;
}

export const createSellerListing = (
  token: string, 
  data: ListingCreatePayload
): Promise<{ message: string; listing: SellerListing; variant?: unknown }> =>
  fetchWithAuth('/seller/listings', token, { method: 'POST', body: data });

export interface ListingUpdatePayload {
  description?: string;
  images?: string[];
  status?: 'draft' | 'active' | 'paused' | 'archived';
  moq?: number;
  stock?: number;
  maxCapacity?: number;
  leadTime?: number;
  datasheetUrl?: string;
  attributes?: Record<string, string | number | boolean>;  // Creates new variant if changed
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
export const exportAdminInquiries = (
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
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
  return fetch(`${apiUrl}/api/admin/inquiries/export?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  }).then(res => {
    if (!res.ok) throw new ApiError('Export failed', res.status);
    return res.blob();
  });
};

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
const MAX_PRODUCT_IMAGE_SIZE = 3 * 1024 * 1024;
const MAX_PRODUCT_IMAGES = 5;

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
  }
): Promise<{
  success: boolean;
  message: string;
  inquiryId: string;
  status: string;
}> => fetchWithAuth('/inquiries', token, {
  method: 'POST',
  body: {
    productId: data.productId,
    sellerId: data.sellerId,
    listingId: data.listingId,
    quantity: data.quantity,
    message: data.message,
    buyerType: data.buyerType,
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
  quote: {
    price: number;
    validTill: string;
  };
  subscriptionUsage: {
    used: number;
    limit: number;
    remaining: number;
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
  sellerRole: string;
  searchableAttributes: Record<string, string | number>;
  attributeLabels: Record<string, string>;
  pricingTiers: PricingTier[];
  lowestPrice?: number;
  moq: number;
  stock: number;
  leadTimeDays?: number;
  images: string[];
  stockStatus: 'in_stock' | 'out_of_stock' | 'limited';
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
  sortBy?: 'price' | 'leadTime' | 'stock' | 'updatedAt';
  order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export interface FilterResponse {
  results: EnterpriseProductSeller[];
  total: number;
  page: number;
  pages: number;
  fallbackLevel: number;
  fallbackMessage?: string;
  appliedFilters: Record<string, unknown>;
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
    body: JSON.stringify(filters),
    headers: { 'Content-Type': 'application/json' }
  });

// Re-export ApiError for consumers
export { ApiError };
