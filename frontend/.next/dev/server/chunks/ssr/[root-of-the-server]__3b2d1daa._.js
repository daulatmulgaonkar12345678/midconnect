module.exports = [
"[project]/frontend/src/app/favicon.ico.mjs { IMAGE => \"[project]/frontend/src/app/favicon.ico (static in ecmascript, tag client)\" } [app-rsc] (structured image object, ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/frontend/src/app/favicon.ico.mjs { IMAGE => \"[project]/frontend/src/app/favicon.ico (static in ecmascript, tag client)\" } [app-rsc] (structured image object, ecmascript)"));
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[project]/frontend/src/app/layout.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/frontend/src/app/layout.tsx [app-rsc] (ecmascript)"));
}),
"[project]/frontend/src/types/api.ts [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * API Types and Error Handling
 */ __turbopack_context__.s([
    "ApiError",
    ()=>ApiError
]);
class ApiError extends Error {
    status;
    code;
    constructor(message, status, code){
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
    }
    /**
   * Check if error is an authentication error
   */ isAuthError() {
        return this.status === 401 || this.status === 403;
    }
    /**
   * Check if error is a network/timeout error
   */ isNetworkError() {
        return this.status === 0 || this.status === 408;
    }
    /**
   * Get user-friendly error message
   */ getUserMessage() {
        switch(this.status){
            case 401:
                return 'Please sign in to continue';
            case 403:
                return 'You do not have permission to perform this action';
            case 404:
                return 'The requested resource was not found';
            case 408:
                return 'Request timed out. Please try again';
            case 429:
                return 'Too many requests. Please wait a moment';
            case 500:
            case 502:
            case 503:
                return 'Server error. Please try again later';
            case 0:
                return 'Network error. Please check your connection';
            default:
                return this.message || 'An error occurred';
        }
    }
}
}),
"[project]/frontend/src/lib/api.ts [app-rsc] (ecmascript) <locals>", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "acceptInquiry",
    ()=>acceptInquiry,
    "activateSubscription",
    ()=>activateSubscription,
    "checkHealth",
    ()=>checkHealth,
    "checkReadiness",
    ()=>checkReadiness,
    "checkRegistrationStatus",
    ()=>checkRegistrationStatus,
    "completeProfile",
    ()=>completeProfile,
    "createAdminCategory",
    ()=>createAdminCategory,
    "createAdminProduct",
    ()=>createAdminProduct,
    "createAdminSpecTemplate",
    ()=>createAdminSpecTemplate,
    "createB2BCategory",
    ()=>createB2BCategory,
    "createB2BSpecTemplate",
    ()=>createB2BSpecTemplate,
    "createGlobalDropdown",
    ()=>createGlobalDropdown,
    "createInquiry",
    ()=>createInquiry,
    "createListing",
    ()=>createListing,
    "createSellerListing",
    ()=>createSellerListing,
    "deleteAccount",
    ()=>deleteAccount,
    "deleteAdminCategory",
    ()=>deleteAdminCategory,
    "deleteAdminProduct",
    ()=>deleteAdminProduct,
    "deleteAdminSpecTemplate",
    ()=>deleteAdminSpecTemplate,
    "deleteB2BSpecTemplate",
    ()=>deleteB2BSpecTemplate,
    "deleteGlobalDropdown",
    ()=>deleteGlobalDropdown,
    "deleteListing",
    ()=>deleteListing,
    "deleteSellerListing",
    ()=>deleteSellerListing,
    "exportAdminInquiries",
    ()=>exportAdminInquiries,
    "extendSubscription",
    ()=>extendSubscription,
    "fetchBase",
    ()=>fetchBase,
    "fetchWithAuth",
    ()=>fetchWithAuth,
    "getAdminAnalytics",
    ()=>getAdminAnalytics,
    "getAdminCategories",
    ()=>getAdminCategories,
    "getAdminInquiries",
    ()=>getAdminInquiries,
    "getAdminKPIMetrics",
    ()=>getAdminKPIMetrics,
    "getAdminProducts",
    ()=>getAdminProducts,
    "getAdminSpecTemplates",
    ()=>getAdminSpecTemplates,
    "getAdminStats",
    ()=>getAdminStats,
    "getAdminSubscription",
    ()=>getAdminSubscription,
    "getAdminUsers",
    ()=>getAdminUsers,
    "getAllCategories",
    ()=>getAllCategories,
    "getB2BCategories",
    ()=>getB2BCategories,
    "getB2BCategory",
    ()=>getB2BCategory,
    "getB2BSpecTemplate",
    ()=>getB2BSpecTemplate,
    "getB2BSpecTemplates",
    ()=>getB2BSpecTemplates,
    "getBuyerInquiries",
    ()=>getBuyerInquiries,
    "getCategories",
    ()=>getCategories,
    "getCategorySpecTemplate",
    ()=>getCategorySpecTemplate,
    "getExpiringSubscriptions",
    ()=>getExpiringSubscriptions,
    "getGlobalDropdown",
    ()=>getGlobalDropdown,
    "getGlobalDropdowns",
    ()=>getGlobalDropdowns,
    "getManufacturers",
    ()=>getManufacturers,
    "getMyCategoryRequests",
    ()=>getMyCategoryRequests,
    "getMyListings",
    ()=>getMyListings,
    "getMyManufacturerRequests",
    ()=>getMyManufacturerRequests,
    "getMyProductRequests",
    ()=>getMyProductRequests,
    "getMySpecFieldRequests",
    ()=>getMySpecFieldRequests,
    "getProduct",
    ()=>getProduct,
    "getProductById",
    ()=>getProductById,
    "getProductWithSellers",
    ()=>getProductWithSellers,
    "getProducts",
    ()=>getProducts,
    "getProductsByCategory",
    ()=>getProductsByCategory,
    "getPublicCategories",
    ()=>getPublicCategories,
    "getSellerDashboard",
    ()=>getSellerDashboard,
    "getSellerInquiries",
    ()=>getSellerInquiries,
    "getSellerListing",
    ()=>getSellerListing,
    "getSellerListings",
    ()=>getSellerListings,
    "getSellerStats",
    ()=>getSellerStats,
    "getSellerStatus",
    ()=>getSellerStatus,
    "getSellerSubscription",
    ()=>getSellerSubscription,
    "getSellerSubscriptionStatus",
    ()=>getSellerSubscriptionStatus,
    "getSpecTemplateById",
    ()=>getSpecTemplateById,
    "getUserProfile",
    ()=>getUserProfile,
    "pauseSellerListing",
    ()=>pauseSellerListing,
    "publishListing",
    ()=>publishListing,
    "publishSellerListing",
    ()=>publishSellerListing,
    "quickPriceUpdate",
    ()=>quickPriceUpdate,
    "reactivateSubscription",
    ()=>reactivateSubscription,
    "registerUser",
    ()=>registerUser,
    "rejectInquiry",
    ()=>rejectInquiry,
    "reportInquiry",
    ()=>reportInquiry,
    "requestCategory",
    ()=>requestCategory,
    "requestManufacturer",
    ()=>requestManufacturer,
    "requestProduct",
    ()=>requestProduct,
    "requestSpecField",
    ()=>requestSpecField,
    "restoreUser",
    ()=>restoreUser,
    "runExpiryCheck",
    ()=>runExpiryCheck,
    "sanitizeInput",
    ()=>sanitizeInput,
    "sanitizeObject",
    ()=>sanitizeObject,
    "searchProducts",
    ()=>searchProducts,
    "seedSystemDropdowns",
    ()=>seedSystemDropdowns,
    "suspendSubscription",
    ()=>suspendSubscription,
    "toggleAdminStatus",
    ()=>toggleAdminStatus,
    "updateAdminCategory",
    ()=>updateAdminCategory,
    "updateAdminProduct",
    ()=>updateAdminProduct,
    "updateAdminSpecTemplate",
    ()=>updateAdminSpecTemplate,
    "updateB2BCategory",
    ()=>updateB2BCategory,
    "updateB2BCategorySettings",
    ()=>updateB2BCategorySettings,
    "updateB2BSpecTemplate",
    ()=>updateB2BSpecTemplate,
    "updateGlobalDropdown",
    ()=>updateGlobalDropdown,
    "updateListing",
    ()=>updateListing,
    "updateSellerListing",
    ()=>updateSellerListing,
    "updateSellerPricing",
    ()=>updateSellerPricing,
    "updateUserProfile",
    ()=>updateUserProfile,
    "uploadCategoryImage",
    ()=>uploadCategoryImage,
    "uploadProductDatasheet",
    ()=>uploadProductDatasheet,
    "uploadProductImages",
    ()=>uploadProductImages,
    "waitForBackend",
    ()=>waitForBackend,
    "warmBackend",
    ()=>warmBackend,
    "warmupBackend",
    ()=>warmupBackend
]);
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
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/src/types/api.ts [app-rsc] (ecmascript)");
;
// API Configuration - uses environment variable only
const API_URL = process.env.NEXT_PUBLIC_API_URL;
if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
;
const DEFAULT_TIMEOUT = 30000; // 30 seconds
function sanitizeInput(input) {
    if (typeof input !== 'string') return '';
    return input.trim().slice(0, 1000).replace(/[<>]/g, '');
}
function sanitizeObject(obj) {
    const sanitized = {};
    for (const [key, value] of Object.entries(obj)){
        if (typeof value === 'string') {
            sanitized[key] = sanitizeInput(value);
        } else if (value !== null && value !== undefined) {
            sanitized[key] = value;
        }
    }
    return sanitized;
}
// ==================== Cold-Start & Retry Configuration ====================
const COLD_START_TIMEOUT = 60000;
const MAX_RETRIES = 3;
const RETRY_DELAYS = [
    2000,
    4000,
    8000
];
const COLD_START_RETRY_DELAYS = [
    3000,
    6000,
    12000
];
let isServerWaking = false;
let serverWarmedUp = false;
let lastSuccessfulRequest = Date.now();
const SERVER_SLEEP_THRESHOLD = 10 * 60 * 1000;
async function warmBackend() {
    if (serverWarmedUp && !mightBeColdStart()) {
        return {
            ready: true,
            message: 'Server is ready'
        };
    }
    const healthUrl = `${API_URL}/health`;
    for(let attempt = 0; attempt < 3; attempt++){
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(()=>controller.abort(), 10000);
            const response = await fetch(healthUrl, {
                method: 'GET',
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (response.ok) {
                serverWarmedUp = true;
                isServerWaking = false;
                lastSuccessfulRequest = Date.now();
                return {
                    ready: true,
                    message: 'Server is ready'
                };
            }
        } catch  {
            console.log(`[API] Health check attempt ${attempt + 1}/3 - server may be waking up`);
            isServerWaking = true;
            if (attempt < 2) {
                await delay(RETRY_DELAYS[attempt] || 2000);
            }
        }
    }
    return {
        ready: false,
        message: 'Server is waking up, please wait...'
    };
}
function getRetryDelay(attempt) {
    const delays = isServerWaking ? COLD_START_RETRY_DELAYS : RETRY_DELAYS;
    return delays[attempt] || delays[delays.length - 1];
}
function mightBeColdStart() {
    return Date.now() - lastSuccessfulRequest > SERVER_SLEEP_THRESHOLD;
}
function delay(ms) {
    return new Promise((resolve)=>setTimeout(resolve, ms));
}
function isRetryableError(error) {
    if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]) {
        if (error.status === 400 || error.status === 401 || error.status === 403) {
            return false;
        }
        return error.status >= 500 || error.status === 0 || error.status === 408;
    }
    if (error instanceof Error) {
        return error.name === 'AbortError' || error.message.includes('fetch') || error.message.includes('network') || error.message.includes('ECONNREFUSED');
    }
    return false;
}
function shouldSkipRetry(endpoint) {
    const noRetryEndpoints = [
        '/users/register',
        '/auth/register'
    ];
    return noRetryEndpoints.some((path)=>endpoint.includes(path));
}
async function fetchAPI(endpoint, options = {}) {
    const { timeout = mightBeColdStart() ? COLD_START_TIMEOUT : DEFAULT_TIMEOUT, body, retries = MAX_RETRIES, skipRetry = shouldSkipRetry(endpoint), ...fetchOptions } = options;
    if (!API_URL) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('API URL not configured', 500, 'CONFIG_ERROR');
    }
    const sanitizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_URL}${sanitizedEndpoint}`;
    let lastError = null;
    const maxAttempts = skipRetry ? 1 : retries + 1;
    for(let attempt = 1; attempt <= maxAttempts; attempt++){
        const controller = new AbortController();
        const timeoutId = setTimeout(()=>controller.abort(), timeout);
        try {
            const response = await fetch(url, {
                ...fetchOptions,
                signal: controller.signal,
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...fetchOptions.headers
                },
                body: body ? JSON.stringify(body) : undefined
            });
            clearTimeout(timeoutId);
            if (!response.ok) {
                let errorData = {};
                try {
                    errorData = await response.json();
                } catch  {
                    errorData = {
                        detail: `HTTP ${response.status}`
                    };
                }
                const error = new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](errorData.detail || errorData.message || `Request failed with status ${response.status}`, response.status, errorData.errorCode);
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
            if (!text) return {};
            return JSON.parse(text);
        } catch (error) {
            clearTimeout(timeoutId);
            if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]) {
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
                    throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](isServerWaking ? 'Server is starting up. Please wait a moment and try again.' : 'Request timeout. Please try again.', 408, 'TIMEOUT');
                }
                throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](error.message || 'Network error', 0, 'NETWORK_ERROR');
            }
            throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Unknown error occurred', 0, 'UNKNOWN');
        }
    }
    throw lastError || new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Request failed after retries', 0, 'RETRY_EXHAUSTED');
}
async function fetchWithAuth(endpoint, token, options = {}) {
    if (!token) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Authentication required', 401, 'AUTH_REQUIRED');
    }
    return fetchAPI(endpoint, {
        ...options,
        headers: {
            ...options.headers,
            Authorization: `Bearer ${token}`
        }
    });
}
const checkHealth = ()=>fetchAPI('/health', {
        skipRetry: true
    });
const checkReadiness = ()=>fetchAPI('/health/ready', {
        skipRetry: true
    });
async function warmupBackend() {
    try {
        await checkHealth();
        lastSuccessfulRequest = Date.now();
        isServerWaking = false;
        return true;
    } catch  {
        isServerWaking = true;
        return false;
    }
}
async function waitForBackend(maxWaitMs = 30000) {
    const startTime = Date.now();
    const checkInterval = 2000;
    while(Date.now() - startTime < maxWaitMs){
        if (await warmupBackend()) {
            return true;
        }
        await delay(checkInterval);
    }
    return false;
}
const fetchBase = fetchAPI;
const getCategories = ()=>fetchAPI('/categories/all');
const getPublicCategories = ()=>fetchAPI('/categories/public');
const getAllCategories = getCategories;
const getProducts = (categoryId)=>{
    const params = categoryId ? `?categoryId=${encodeURIComponent(categoryId)}` : '';
    return fetchAPI(`/products${params}`);
};
const getProduct = (productId)=>fetchAPI(`/products/${encodeURIComponent(productId)}`);
const getProductWithSellers = (productIdentifier)=>fetchAPI(`/products/detail/${encodeURIComponent(productIdentifier)}`);
const searchProducts = (query, options = {})=>{
    const sanitizedQuery = sanitizeInput(query);
    return fetchAPI('/search/products', {
        method: 'POST',
        body: {
            query: sanitizedQuery,
            categoryId: options.categoryId ? encodeURIComponent(options.categoryId) : undefined,
            limit: Math.min(options.limit || 50, 100),
            skip: Math.max(options.skip || 0, 0)
        }
    });
};
const getUserProfile = (token)=>fetchWithAuth('/users/me', token);
const updateUserProfile = (token, data)=>fetchWithAuth('/users/me', token, {
        method: 'PUT',
        body: sanitizeObject(data)
    });
const registerUser = (token, data)=>fetchWithAuth('/users/register', token, {
        method: 'POST',
        body: {
            email: data.email,
            firebaseUid: data.firebaseUid,
            businessName: data.businessName,
            phone: data.phone,
            city: data.city,
            state: data.state,
            pincode: data.pincode
        }
    });
const checkRegistrationStatus = (token)=>fetchWithAuth('/auth/check-registration', token);
const completeProfile = (token, data)=>fetchWithAuth('/auth/complete-profile', token, {
        method: 'POST',
        body: {
            role: data.role,
            businessName: data.businessName,
            phone: data.phone,
            address: data.address,
            city: data.city,
            state: data.state,
            pincode: data.pincode,
            gstNumber: data.gstNumber || undefined
        }
    });
const getSellerStatus = (token)=>fetchWithAuth('/seller/status', token);
const deleteAccount = (token, reason = '')=>fetchWithAuth('/users/me/delete', token, {
        method: 'POST',
        body: {
            confirmation: true,
            reason: sanitizeInput(reason)
        }
    });
const getSellerStats = (token)=>fetchWithAuth('/seller/stats', token);
const getMyListings = (token)=>fetchWithAuth('/seller/listings', token).then((res)=>res.listings || []);
const createListing = (token, data)=>fetchWithAuth('/seller/listings', token, {
        method: 'POST',
        body: sanitizeObject(data)
    });
const updateListing = (token, listingId, data)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, {
        method: 'PATCH',
        body: sanitizeObject(data)
    });
const quickPriceUpdate = (token, listingId, data)=>updateListing(token, listingId, data);
const publishListing = (token, listingId)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/publish`, token, {
        method: 'POST'
    });
const deleteListing = (token, listingId)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, {
        method: 'DELETE'
    });
const getAdminStats = (token)=>fetchWithAuth('/admin/stats', token);
const getAdminCategories = (token, includeInactive = false)=>fetchWithAuth(`/admin/categories?includeInactive=${includeInactive}`, token);
const createAdminCategory = (token, data)=>fetchWithAuth('/admin/categories', token, {
        method: 'POST',
        body: sanitizeObject(data)
    });
const updateAdminCategory = (token, id, data)=>fetchWithAuth(`/admin/categories/${encodeURIComponent(id)}`, token, {
        method: 'PATCH',
        body: sanitizeObject(data)
    });
const deleteAdminCategory = (token, id, force = false)=>fetchWithAuth(`/admin/categories/${encodeURIComponent(id)}?force=${force}`, token, {
        method: 'DELETE'
    });
const getAdminUsers = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.search) params.append('search', sanitizeInput(options.search));
    if (options?.status) params.append('status', options.status);
    if (options?.isSeller !== undefined) params.append('isSeller', options.isSeller.toString());
    if (options?.page) params.append('page', Math.max(1, options.page).toString());
    if (options?.limit) params.append('limit', Math.min(options.limit || 20, 100).toString());
    return fetchWithAuth(`/admin/users?${params.toString()}`, token);
};
const toggleAdminStatus = (token, userId)=>fetchWithAuth(`/admin/users/${encodeURIComponent(userId)}/toggle-admin`, token, {
        method: 'PATCH'
    });
const restoreUser = (token, userId)=>fetchWithAuth(`/admin/users/${encodeURIComponent(userId)}/restore`, token, {
        method: 'POST'
    });
const getAdminProducts = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.categoryId) params.append('categoryId', options.categoryId);
    if (options?.search) params.append('search', sanitizeInput(options.search));
    if (options?.includeInactive) params.append('includeInactive', 'true');
    if (options?.page) params.append('page', Math.max(1, options.page).toString());
    if (options?.limit) params.append('limit', Math.min(options.limit || 20, 100).toString());
    return fetchWithAuth(`/admin/products?${params.toString()}`, token);
};
const createAdminProduct = (token, data)=>fetchWithAuth('/admin/products', token, {
        method: 'POST',
        body: sanitizeObject(data)
    });
const updateAdminProduct = (token, id, data)=>fetchWithAuth(`/admin/products/${encodeURIComponent(id)}`, token, {
        method: 'PATCH',
        body: sanitizeObject(data)
    });
const deleteAdminProduct = (token, id, force = false)=>fetchWithAuth(`/admin/products/${encodeURIComponent(id)}?force=${force}`, token, {
        method: 'DELETE'
    });
const getAdminSpecTemplates = (token, categoryId, includeInactive = false)=>{
    const params = new URLSearchParams();
    params.append('includeInactive', includeInactive.toString());
    if (categoryId) params.append('categoryId', categoryId);
    return fetchWithAuth(`/admin/spec-templates?${params.toString()}`, token);
};
const createAdminSpecTemplate = (token, data)=>fetchWithAuth('/admin/spec-templates', token, {
        method: 'POST',
        body: sanitizeObject(data)
    });
const updateAdminSpecTemplate = (token, id, data)=>fetchWithAuth(`/admin/spec-templates/${encodeURIComponent(id)}`, token, {
        method: 'PATCH',
        body: sanitizeObject(data)
    });
const deleteAdminSpecTemplate = (token, id, force = false)=>fetchWithAuth(`/admin/spec-templates/${encodeURIComponent(id)}?force=${force}`, token, {
        method: 'DELETE'
    });
const getGlobalDropdowns = (token, options)=>{
    const params = new URLSearchParams();
    params.append('includeInactive', (options?.includeInactive ?? false).toString());
    params.append('includeSystem', (options?.includeSystem ?? true).toString());
    return fetchWithAuth(`/admin/b2b/dropdowns?${params.toString()}`, token);
};
const getGlobalDropdown = (token, key)=>fetchWithAuth(`/admin/b2b/dropdowns/${encodeURIComponent(key)}`, token);
const createGlobalDropdown = (token, data)=>fetchWithAuth('/admin/b2b/dropdowns', token, {
        method: 'POST',
        body: data
    });
const updateGlobalDropdown = (token, key, data)=>fetchWithAuth(`/admin/b2b/dropdowns/${encodeURIComponent(key)}`, token, {
        method: 'PATCH',
        body: data
    });
const deleteGlobalDropdown = (token, key, force = false)=>fetchWithAuth(`/admin/b2b/dropdowns/${encodeURIComponent(key)}?force=${force}`, token, {
        method: 'DELETE'
    });
const seedSystemDropdowns = (token)=>fetchWithAuth('/admin/b2b/seed-system-dropdowns', token, {
        method: 'POST'
    });
const getB2BCategories = (token, includeInactive = false)=>fetchWithAuth(`/admin/b2b/categories?includeInactive=${includeInactive}`, token);
const getB2BCategory = (token, categoryId)=>fetchWithAuth(`/admin/b2b/categories/${encodeURIComponent(categoryId)}`, token);
const createB2BCategory = (token, data)=>fetchWithAuth('/admin/b2b/categories', token, {
        method: 'POST',
        body: data
    });
const updateB2BCategory = (token, categoryId, data)=>fetchWithAuth(`/admin/b2b/categories/${encodeURIComponent(categoryId)}`, token, {
        method: 'PATCH',
        body: data
    });
const updateB2BCategorySettings = (token, categoryId, settings)=>fetchWithAuth(`/admin/b2b/categories/${encodeURIComponent(categoryId)}/settings`, token, {
        method: 'PATCH',
        body: settings
    });
const getB2BSpecTemplates = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.categoryId) params.append('categoryId', options.categoryId);
    params.append('includeInactive', (options?.includeInactive ?? false).toString());
    return fetchWithAuth(`/admin/b2b/spec-templates?${params.toString()}`, token);
};
const getB2BSpecTemplate = (token, templateId)=>fetchWithAuth(`/admin/b2b/spec-templates/${encodeURIComponent(templateId)}`, token);
const createB2BSpecTemplate = (token, data)=>fetchWithAuth('/admin/b2b/spec-templates', token, {
        method: 'POST',
        body: data
    });
const updateB2BSpecTemplate = (token, templateId, data)=>fetchWithAuth(`/admin/b2b/spec-templates/${encodeURIComponent(templateId)}`, token, {
        method: 'PATCH',
        body: data
    });
const deleteB2BSpecTemplate = (token, templateId, force = false)=>fetchWithAuth(`/admin/b2b/spec-templates/${encodeURIComponent(templateId)}?force=${force}`, token, {
        method: 'DELETE'
    });
const getSellerDashboard = (token)=>fetchWithAuth('/seller/dashboard', token);
const getSellerListings = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.status) params.append('status', options.status);
    if (options?.categoryId) params.append('categoryId', options.categoryId);
    if (options?.page) params.append('page', options.page.toString());
    if (options?.limit) params.append('limit', options.limit.toString());
    return fetchWithAuth(`/seller/listings?${params.toString()}`, token);
};
const getSellerListing = (token, listingId)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token);
const createSellerListing = (token, data)=>fetchWithAuth('/seller/listings', token, {
        method: 'POST',
        body: data
    });
const updateSellerListing = (token, listingId, data)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}`, token, {
        method: 'PATCH',
        body: data
    });
const getProductById = (productId)=>fetchAPI(`/products/${encodeURIComponent(productId)}`);
const getSpecTemplateById = (token, templateId)=>fetchWithAuth(`/spec-templates/${encodeURIComponent(templateId)}`, token);
const updateSellerPricing = (token, listingId, data)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/pricing`, token, {
        method: 'PATCH',
        body: data
    });
const publishSellerListing = (token, listingId)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/publish`, token, {
        method: 'POST'
    });
const pauseSellerListing = (token, listingId)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}/pause`, token, {
        method: 'POST'
    });
const deleteSellerListing = (token, listingId, hardDelete = false)=>fetchWithAuth(`/seller/listings/${encodeURIComponent(listingId)}?hardDelete=${hardDelete}`, token, {
        method: 'DELETE'
    });
const getSellerSubscription = (token)=>fetchWithAuth('/seller/subscription', token);
const getSellerSubscriptionStatus = (token)=>fetchWithAuth('/seller/subscription/status', token);
const getAdminInquiries = (token, options)=>{
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
const getAdminAnalytics = (token, days = 30)=>fetchWithAuth(`/admin/analytics?days=${days}`, token);
const getAdminKPIMetrics = (token)=>fetchWithAuth('/admin/kpi-metrics', token);
const getAdminSubscription = (token, userId)=>fetchWithAuth(`/admin/subscriptions/manage/${userId}`, token);
const activateSubscription = (token, userId, data)=>fetchWithAuth(`/admin/subscriptions/activate/${userId}`, token, {
        method: 'POST',
        body: data
    });
const extendSubscription = (token, userId, data)=>fetchWithAuth(`/admin/subscriptions/extend/${userId}`, token, {
        method: 'POST',
        body: data
    });
const suspendSubscription = (token, userId, reason)=>fetchWithAuth(`/admin/subscriptions/suspend/${userId}`, token, {
        method: 'POST',
        body: {
            reason
        }
    });
const reactivateSubscription = (token, userId)=>fetchWithAuth(`/admin/subscriptions/reactivate/${userId}`, token, {
        method: 'POST'
    });
const runExpiryCheck = (token)=>fetchWithAuth('/admin/subscriptions/run-expiry-check', token, {
        method: 'POST'
    });
const getExpiringSubscriptions = (token, days = 10)=>fetchWithAuth(`/admin/subscriptions/expiring?days=${days}`, token);
const exportAdminInquiries = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.status) params.append('status', options.status);
    if (options?.sellerId) params.append('sellerId', options.sellerId);
    if (options?.buyerId) params.append('buyerId', options.buyerId);
    if (options?.dateFrom) params.append('dateFrom', options.dateFrom);
    if (options?.dateTo) params.append('dateTo', options.dateTo);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
    return fetch(`${apiUrl}/api/admin/inquiries/export?${params.toString()}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    }).then((res)=>{
        if (!res.ok) throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Export failed', res.status);
        return res.blob();
    });
};
const getCategorySpecTemplate = (token, categoryId)=>fetchWithAuth(`/seller/categories/${encodeURIComponent(categoryId)}/spec-template`, token);
// ==================== Image Upload ====================
const ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/webp',
    'image/heic',
    'image/heif'
];
const MAX_CATEGORY_IMAGE_SIZE = 1 * 1024 * 1024;
const MAX_PRODUCT_IMAGE_SIZE = 3 * 1024 * 1024;
const MAX_PRODUCT_IMAGES = 5;
function validateImageFile(file, maxSize, context) {
    const fileType = file.type.toLowerCase();
    const fileName = file.name.toLowerCase();
    const isValidType = ALLOWED_IMAGE_TYPES.includes(fileType) || fileName.endsWith('.jpg') || fileName.endsWith('.jpeg') || fileName.endsWith('.png') || fileName.endsWith('.webp') || fileName.endsWith('.heic') || fileName.endsWith('.heif');
    if (!isValidType) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](`Invalid image type for ${context}. Allowed: JPEG, PNG, WEBP`, 400, 'INVALID_IMAGE_TYPE');
    }
    if (file.size > maxSize) {
        const maxMB = (maxSize / (1024 * 1024)).toFixed(1);
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](`Image too large. Maximum size: ${maxMB} MB`, 400, 'IMAGE_TOO_LARGE');
    }
}
async function uploadCategoryImage(token, file) {
    validateImageFile(file, MAX_CATEGORY_IMAGE_SIZE, 'category');
    const { uploadAdminCategoryImage } = await __turbopack_context__.A("[project]/frontend/src/lib/cloudinary.ts [app-rsc] (ecmascript, async loader)");
    const result = await uploadAdminCategoryImage(file);
    return {
        imageUrl: result.url
    };
}
async function uploadProductImages(token, files) {
    if (files.length === 0) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('At least one image is required', 400);
    }
    if (files.length > MAX_PRODUCT_IMAGES) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"](`Maximum ${MAX_PRODUCT_IMAGES} images allowed`, 400);
    }
    files.forEach((file, idx)=>{
        validateImageFile(file, MAX_PRODUCT_IMAGE_SIZE, `product image ${idx + 1}`);
    });
    const { uploadSellerProductImage } = await __turbopack_context__.A("[project]/frontend/src/lib/cloudinary.ts [app-rsc] (ecmascript, async loader)");
    const uploadPromises = files.map((file)=>uploadSellerProductImage(file));
    const results = await Promise.all(uploadPromises);
    return {
        images: results.map((r)=>r.url)
    };
}
async function uploadProductDatasheet(token, file) {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Only PDF files are allowed for datasheets', 400, 'INVALID_FILE_TYPE');
    }
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["ApiError"]('Datasheet file must be less than 5MB', 400, 'FILE_TOO_LARGE');
    }
    const { uploadSellerDatasheet } = await __turbopack_context__.A("[project]/frontend/src/lib/cloudinary.ts [app-rsc] (ecmascript, async loader)");
    const result = await uploadSellerDatasheet(file);
    return {
        url: result.url
    };
}
const requestManufacturer = (token, data)=>fetchWithAuth('/seller/requests/manufacturer', token, {
        method: 'POST',
        body: data
    });
const getMyManufacturerRequests = (token, status)=>fetchWithAuth(`/seller/requests/manufacturer${status ? `?status=${status}` : ''}`, token);
const requestProduct = (token, data)=>fetchWithAuth('/seller/requests/product', token, {
        method: 'POST',
        body: {
            productName: data.productName,
            suggestedCategoryId: data.suggestedCategoryId,
            manufacturerId: data.manufacturerId,
            description: data.description,
            reason: data.reason
        }
    });
const getMyProductRequests = (token, status)=>fetchWithAuth(`/seller/requests/product${status ? `?status=${status}` : ''}`, token);
const requestCategory = (token, data)=>fetchWithAuth('/seller/requests/category', token, {
        method: 'POST',
        body: {
            categoryName: data.categoryName,
            description: data.description,
            reason: data.reason
        }
    });
const getMyCategoryRequests = (token, status)=>fetchWithAuth(`/seller/requests/category${status ? `?status=${status}` : ''}`, token);
const requestSpecField = (token, data)=>fetchWithAuth('/seller/requests/spec-field', token, {
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
const getMySpecFieldRequests = (token, status)=>fetchWithAuth(`/seller/requests/spec-field${status ? `?status=${status}` : ''}`, token);
const getProductsByCategory = (categoryId)=>fetchBase(`/products/by-category/${encodeURIComponent(categoryId)}`);
const getManufacturers = (categoryId, search)=>{
    const params = new URLSearchParams();
    if (categoryId) params.append('categoryId', categoryId);
    if (search) params.append('search', search);
    return fetchBase(`/manufacturers?${params.toString()}`);
};
const createInquiry = (token, data)=>fetchWithAuth('/inquiries', token, {
        method: 'POST',
        body: {
            productId: data.productId,
            sellerId: data.sellerId,
            listingId: data.listingId,
            quantity: data.quantity,
            message: data.message,
            buyerType: data.buyerType
        }
    });
const getBuyerInquiries = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.status) params.append('status', options.status);
    if (options?.page) params.append('page', String(options.page));
    if (options?.limit) params.append('limit', String(options.limit));
    return fetchWithAuth(`/buyer/inquiries?${params.toString()}`, token);
};
const getSellerInquiries = (token, options)=>{
    const params = new URLSearchParams();
    if (options?.status) params.append('status', options.status);
    if (options?.page) params.append('page', String(options.page));
    if (options?.limit) params.append('limit', String(options.limit));
    return fetchWithAuth(`/seller/inquiries?${params.toString()}`, token);
};
const acceptInquiry = (token, inquiryId, data)=>fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/accept`, token, {
        method: 'POST',
        body: data
    });
const rejectInquiry = (token, inquiryId, data)=>fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/reject`, token, {
        method: 'POST',
        body: data
    });
const reportInquiry = (token, inquiryId, data)=>fetchWithAuth(`/seller/inquiries/${encodeURIComponent(inquiryId)}/report`, token, {
        method: 'POST',
        body: data
    });
;
}),
"[project]/frontend/src/components/CategoryCard.tsx [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>CategoryCard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-jsx-dev-runtime.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/client/app-dir/link.react-server.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$zap$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Zap$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/zap.js [app-rsc] (ecmascript) <export default as Zap>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$flask$2d$round$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__FlaskRound$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/flask-round.js [app-rsc] (ecmascript) <export default as FlaskRound>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Building2$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/building-2.js [app-rsc] (ecmascript) <export default as Building2>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$settings$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Settings$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/settings.js [app-rsc] (ecmascript) <export default as Settings>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shield$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Shield$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/shield.js [app-rsc] (ecmascript) <export default as Shield>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$package$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Package$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/package.js [app-rsc] (ecmascript) <export default as Package>");
;
;
;
const iconMap = {
    'flash-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$zap$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Zap$3e$__["Zap"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 8,
        columnNumber: 20
    }, ("TURBOPACK compile-time value", void 0)),
    'cube-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$package$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Package$3e$__["Package"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 9,
        columnNumber: 19
    }, ("TURBOPACK compile-time value", void 0)),
    'flask-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$flask$2d$round$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__FlaskRound$3e$__["FlaskRound"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 10,
        columnNumber: 20
    }, ("TURBOPACK compile-time value", void 0)),
    'business-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$building$2d$2$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Building2$3e$__["Building2"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 11,
        columnNumber: 23
    }, ("TURBOPACK compile-time value", void 0)),
    'settings-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$settings$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Settings$3e$__["Settings"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 12,
        columnNumber: 23
    }, ("TURBOPACK compile-time value", void 0)),
    'shield-outline': /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shield$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Shield$3e$__["Shield"], {
        className: "h-8 w-8"
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 13,
        columnNumber: 21
    }, ("TURBOPACK compile-time value", void 0))
};
function CategoryCard({ category }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
        href: `/category/${category._id}`,
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:border-blue-200 transition-all group",
            children: [
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "text-blue-600 mb-4 group-hover:scale-110 transition-transform",
                    children: category.icon && iconMap[category.icon] ? iconMap[category.icon] : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$package$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Package$3e$__["Package"], {
                        className: "h-8 w-8"
                    }, void 0, false, {
                        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
                        lineNumber: 25,
                        columnNumber: 79
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/frontend/src/components/CategoryCard.tsx",
                    lineNumber: 24,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                    className: "font-semibold text-gray-900 mb-2",
                    children: category.name
                }, void 0, false, {
                    fileName: "[project]/frontend/src/components/CategoryCard.tsx",
                    lineNumber: 27,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                    className: "text-sm text-gray-500 line-clamp-2",
                    children: category.description
                }, void 0, false, {
                    fileName: "[project]/frontend/src/components/CategoryCard.tsx",
                    lineNumber: 28,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/frontend/src/components/CategoryCard.tsx",
            lineNumber: 23,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/CategoryCard.tsx",
        lineNumber: 22,
        columnNumber: 5
    }, this);
}
}),
"[project]/frontend/src/components/ProductCard.tsx [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>ProductCard
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-jsx-dev-runtime.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/client/app-dir/link.react-server.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$map$2d$pin$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__MapPin$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/map-pin.js [app-rsc] (ecmascript) <export default as MapPin>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$users$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Users$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/users.js [app-rsc] (ecmascript) <export default as Users>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trending$2d$up$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__TrendingUp$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/trending-up.js [app-rsc] (ecmascript) <export default as TrendingUp>");
;
;
;
// Badge styling based on type
const badgeStyles = {
    local: 'bg-green-100 text-green-700 border-green-200',
    best_value: 'bg-blue-100 text-blue-700 border-blue-200',
    fast: 'bg-purple-100 text-purple-700 border-purple-200',
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200'
};
// Seller type badges with emojis
const SELLER_TYPE_BADGES = {
    manufacturer: {
        emoji: '🏭',
        label: 'Manufacturer',
        color: 'bg-indigo-100 text-indigo-700'
    },
    dealer: {
        emoji: '🏷️',
        label: 'Dealer',
        color: 'bg-blue-100 text-blue-700'
    },
    distributor: {
        emoji: '🚚',
        label: 'Distributor',
        color: 'bg-orange-100 text-orange-700'
    },
    wholesaler: {
        emoji: '📦',
        label: 'Wholesaler',
        color: 'bg-purple-100 text-purple-700'
    },
    retailer: {
        emoji: '🛍️',
        label: 'Retailer',
        color: 'bg-pink-100 text-pink-700'
    }
};
function ProductCard({ product }) {
    const firstSeller = product.sellers?.[0];
    const thumbnail = firstSeller?.images?.[0] || '/placeholder-product.png';
    // Get seller type from first seller's role - camelCase
    const sellerType = firstSeller?.sellerRole?.toLowerCase();
    const sellerBadge = sellerType ? SELLER_TYPE_BADGES[sellerType] : null;
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
        href: `/product/${product.productId}`,
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow relative",
            children: [
                product.badge && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: `absolute top-2 left-2 z-10 px-2 py-1 rounded-full text-xs font-medium border ${badgeStyles[product.badgeType || 'best_value']}`,
                    children: product.badge
                }, void 0, false, {
                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                    lineNumber: 42,
                    columnNumber: 11
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "aspect-[4/3] bg-gray-100 relative",
                    children: [
                        thumbnail && thumbnail !== '/placeholder-product.png' ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("img", {
                            src: thumbnail,
                            alt: product.productName,
                            className: "w-full h-full object-cover"
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 50,
                            columnNumber: 13
                        }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "w-full h-full flex items-center justify-center text-gray-400",
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                className: "text-4xl",
                                children: "📦"
                            }, void 0, false, {
                                fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                lineNumber: 57,
                                columnNumber: 15
                            }, this)
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 56,
                            columnNumber: 13
                        }, this),
                        product.sellerCount > 1 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "absolute top-2 right-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$users$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Users$3e$__["Users"], {
                                    className: "h-3 w-3"
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 62,
                                    columnNumber: 15
                                }, this),
                                product.sellerCount,
                                " sellers"
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 61,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                    lineNumber: 48,
                    columnNumber: 9
                }, this),
                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "p-4",
                    children: [
                        sellerBadge && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium mb-2 ${sellerBadge.color}`,
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    children: sellerBadge.emoji
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 73,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    children: sellerBadge.label
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 74,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 72,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "text-xs text-blue-600 font-medium mb-1",
                            children: product.categoryName
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 78,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                            className: "font-semibold text-gray-900 mb-1 line-clamp-2",
                            children: product.productName
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 81,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "text-sm text-gray-500 mb-3",
                            children: [
                                product.productFamily,
                                " • ",
                                product.productVariant
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 84,
                            columnNumber: 11
                        }, this),
                        product.minPrice && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex items-center gap-1 text-lg font-bold text-green-600",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$trending$2d$up$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__TrendingUp$3e$__["TrendingUp"], {
                                    className: "h-4 w-4"
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 91,
                                    columnNumber: 15
                                }, this),
                                "₹",
                                product.minPrice.toLocaleString(),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "text-xs text-gray-500 font-normal",
                                    children: [
                                        "/",
                                        product.productUnit
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 93,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 90,
                            columnNumber: 13
                        }, this),
                        firstSeller?.sellerArea && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex items-center gap-1 text-sm text-gray-500 mt-2",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$map$2d$pin$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__MapPin$3e$__["MapPin"], {
                                    className: "h-4 w-4"
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 100,
                                    columnNumber: 15
                                }, this),
                                firstSeller.sellerArea,
                                ", ",
                                firstSeller.sellerState,
                                firstSeller.locationClass === 'LOCAL' && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                    className: "ml-1 text-xs text-green-600",
                                    children: "(Local)"
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                                    lineNumber: 103,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/components/ProductCard.tsx",
                            lineNumber: 99,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/frontend/src/components/ProductCard.tsx",
                    lineNumber: 69,
                    columnNumber: 9
                }, this)
            ]
        }, void 0, true, {
            fileName: "[project]/frontend/src/components/ProductCard.tsx",
            lineNumber: 39,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/frontend/src/components/ProductCard.tsx",
        lineNumber: 38,
        columnNumber: 5
    }, this);
}
}),
"[project]/frontend/src/app/page.tsx [app-rsc] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>HomePage,
    "revalidate",
    ()=>revalidate
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/server/route-modules/app-page/vendored/rsc/react-jsx-dev-runtime.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/node_modules/next/dist/client/app-dir/link.react-server.js [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/frontend/src/lib/api.ts [app-rsc] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$components$2f$CategoryCard$2e$tsx__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/src/components/CategoryCard.tsx [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$components$2f$ProductCard$2e$tsx__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/frontend/src/components/ProductCard.tsx [app-rsc] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$right$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowRight$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/arrow-right.js [app-rsc] (ecmascript) <export default as ArrowRight>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shield$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Shield$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/shield.js [app-rsc] (ecmascript) <export default as Shield>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$truck$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Truck$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/truck.js [app-rsc] (ecmascript) <export default as Truck>");
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$badge$2d$check$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__BadgeCheck$3e$__ = __turbopack_context__.i("[project]/frontend/node_modules/lucide-react/dist/esm/icons/badge-check.js [app-rsc] (ecmascript) <export default as BadgeCheck>");
;
;
;
;
;
;
const revalidate = 3600; // Revalidate every hour
async function HomePage() {
    let categories = [];
    let featuredProducts = [];
    try {
        categories = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getCategories"])();
        const searchResult = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$locals$3e$__["searchProducts"])('');
        featuredProducts = searchResult.products?.slice(0, 8) || [];
    } catch (error) {
        console.error('Failed to fetch data:', error);
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "bg-gradient-to-br from-blue-600 to-blue-800 text-white",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "max-w-3xl",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                className: "text-4xl md:text-5xl font-bold mb-6",
                                children: "India's Trusted MidConnect Marketplace for Industrial Products"
                            }, void 0, false, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 28,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "text-xl text-blue-100 mb-8",
                                children: "Connect directly with verified manufacturers, dealers, and distributors. No middlemen. Best prices. Trusted quality."
                            }, void 0, false, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 31,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex flex-col sm:flex-row gap-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/products",
                                        className: "bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition flex items-center justify-center gap-2",
                                        children: [
                                            "Browse Products ",
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$right$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowRight$3e$__["ArrowRight"], {
                                                className: "h-5 w-5"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 40,
                                                columnNumber: 33
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 36,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/sell",
                                        className: "border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white/10 transition text-center",
                                        children: "Start Selling"
                                    }, void 0, false, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 42,
                                        columnNumber: 15
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 35,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/frontend/src/app/page.tsx",
                        lineNumber: 27,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/frontend/src/app/page.tsx",
                    lineNumber: 26,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/frontend/src/app/page.tsx",
                lineNumber: 25,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "bg-gray-50 py-8 border-b",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "grid grid-cols-1 md:grid-cols-3 gap-6",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "bg-green-100 p-3 rounded-full",
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$badge$2d$check$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__BadgeCheck$3e$__["BadgeCheck"], {
                                            className: "h-6 w-6 text-green-600"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 59,
                                            columnNumber: 17
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 58,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                                className: "font-semibold",
                                                children: "GST Verified Sellers"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 62,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                className: "text-sm text-gray-500",
                                                children: "All sellers are verified"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 63,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 61,
                                        columnNumber: 15
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 57,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "bg-blue-100 p-3 rounded-full",
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shield$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Shield$3e$__["Shield"], {
                                            className: "h-6 w-6 text-blue-600"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 68,
                                            columnNumber: 17
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 67,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                                className: "font-semibold",
                                                children: "Secure Transactions"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 71,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                className: "text-sm text-gray-500",
                                                children: "Direct buyer-seller connect"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 72,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 70,
                                        columnNumber: 15
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 66,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "bg-orange-100 p-3 rounded-full",
                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$truck$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__Truck$3e$__["Truck"], {
                                            className: "h-6 w-6 text-orange-600"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 77,
                                            columnNumber: 17
                                        }, this)
                                    }, void 0, false, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 76,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h3", {
                                                className: "font-semibold",
                                                children: "Pan India Delivery"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 80,
                                                columnNumber: 17
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                className: "text-sm text-gray-500",
                                                children: "Nationwide coverage"
                                            }, void 0, false, {
                                                fileName: "[project]/frontend/src/app/page.tsx",
                                                lineNumber: 81,
                                                columnNumber: 17
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/frontend/src/app/page.tsx",
                                        lineNumber: 79,
                                        columnNumber: 15
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/frontend/src/app/page.tsx",
                                lineNumber: 75,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/frontend/src/app/page.tsx",
                        lineNumber: 56,
                        columnNumber: 11
                    }, this)
                }, void 0, false, {
                    fileName: "[project]/frontend/src/app/page.tsx",
                    lineNumber: 55,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/frontend/src/app/page.tsx",
                lineNumber: 54,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "py-16",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex justify-between items-center mb-8",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                            className: "text-2xl font-bold text-gray-900",
                                            children: "Browse by Category"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 93,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "text-gray-500 mt-1",
                                            children: "Explore industrial products across categories"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 94,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 92,
                                    columnNumber: 13
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                    href: "/categories",
                                    className: "text-blue-600 hover:text-blue-700 flex items-center gap-1",
                                    children: [
                                        "View All ",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$right$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowRight$3e$__["ArrowRight"], {
                                            className: "h-4 w-4"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 97,
                                            columnNumber: 24
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 96,
                                    columnNumber: 13
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 91,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6",
                            children: categories.slice(0, 8).map((category)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$components$2f$CategoryCard$2e$tsx__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                    category: category
                                }, category._id, false, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 102,
                                    columnNumber: 15
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 100,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/frontend/src/app/page.tsx",
                    lineNumber: 90,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/frontend/src/app/page.tsx",
                lineNumber: 89,
                columnNumber: 7
            }, this),
            featuredProducts.length > 0 && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "py-16 bg-gray-50",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "flex justify-between items-center mb-8",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                                            className: "text-2xl font-bold text-gray-900",
                                            children: "Featured Products"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 114,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                            className: "text-gray-500 mt-1",
                                            children: "Latest listings from verified sellers"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 115,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 113,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                    href: "/products",
                                    className: "text-blue-600 hover:text-blue-700 flex items-center gap-1",
                                    children: [
                                        "View All ",
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$right$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowRight$3e$__["ArrowRight"], {
                                            className: "h-4 w-4"
                                        }, void 0, false, {
                                            fileName: "[project]/frontend/src/app/page.tsx",
                                            lineNumber: 118,
                                            columnNumber: 26
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 117,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 112,
                            columnNumber: 13
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6",
                            children: featuredProducts.map((product)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$src$2f$components$2f$ProductCard$2e$tsx__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                                    product: product
                                }, product.productId, false, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 123,
                                    columnNumber: 17
                                }, this))
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 121,
                            columnNumber: 13
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/frontend/src/app/page.tsx",
                    lineNumber: 111,
                    columnNumber: 11
                }, this)
            }, void 0, false, {
                fileName: "[project]/frontend/src/app/page.tsx",
                lineNumber: 110,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("section", {
                className: "py-16 bg-blue-600",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                    className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("h2", {
                            className: "text-3xl font-bold text-white mb-4",
                            children: "Ready to Start Selling?"
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 133,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                            className: "text-blue-100 mb-8 max-w-2xl mx-auto",
                            children: "Join thousands of verified sellers on India's fastest growing B2B marketplace. List your products and reach buyers across India."
                        }, void 0, false, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 134,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$react$2d$server$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["default"], {
                            href: "/sell",
                            className: "bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition inline-flex items-center gap-2",
                            children: [
                                "Register as Seller ",
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$rsc$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$arrow$2d$right$2e$js__$5b$app$2d$rsc$5d$__$28$ecmascript$29$__$3c$export__default__as__ArrowRight$3e$__["ArrowRight"], {
                                    className: "h-5 w-5"
                                }, void 0, false, {
                                    fileName: "[project]/frontend/src/app/page.tsx",
                                    lineNumber: 142,
                                    columnNumber: 32
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/frontend/src/app/page.tsx",
                            lineNumber: 138,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/frontend/src/app/page.tsx",
                    lineNumber: 132,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/frontend/src/app/page.tsx",
                lineNumber: 131,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/frontend/src/app/page.tsx",
        lineNumber: 23,
        columnNumber: 5
    }, this);
}
}),
"[project]/frontend/src/app/page.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/frontend/src/app/page.tsx [app-rsc] (ecmascript)"));
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__3b2d1daa._.js.map