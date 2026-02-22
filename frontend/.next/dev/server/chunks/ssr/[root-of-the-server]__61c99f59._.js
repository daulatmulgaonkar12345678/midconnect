module.exports = [
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[project]/src/lib/firebase.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "app",
    ()=>app,
    "auth",
    ()=>auth,
    "default",
    ()=>__TURBOPACK__default__export__,
    "getIdToken",
    ()=>getIdToken,
    "onAuthChange",
    ()=>onAuthChange,
    "signIn",
    ()=>signIn,
    "signOut",
    ()=>signOut,
    "signUp",
    ()=>signUp
]);
/**
 * Firebase Configuration for Next.js Website
 * 
 * This is a WEB-ONLY configuration:
 * - Uses standard Firebase Web SDK
 * - Browser persistence (localStorage/indexedDB) handled automatically
 * - NO React Native dependencies
 * - Same Firebase project as mobile app
 * 
 * For mobile, use frontend-mobile/src/config/firebase.ts instead
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$firebase$2f$app$2f$dist$2f$index$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/firebase/app/dist/index.mjs [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$app$2f$dist$2f$esm$2f$index$2e$esm$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/@firebase/app/dist/esm/index.esm.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$firebase$2f$auth$2f$dist$2f$index$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/firebase/auth/dist/index.mjs [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/@firebase/auth/dist/node-esm/index.js [app-ssr] (ecmascript)");
;
;
// Firebase configuration - same project as mobile app
// Tokens generated here are compatible with backend verification
const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyAhug_bZOGZ-r6658RA0y0VdXXzKWGCLzc",
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "midcconnect.firebaseapp.com",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "midcconnect",
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "midcconnect.firebasestorage.app",
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "212771645719",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:212771645719:web:default"
};
// Initialize Firebase app (singleton pattern)
let app;
if ((0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$app$2f$dist$2f$esm$2f$index$2e$esm$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApps"])().length === 0) {
    app = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$app$2f$dist$2f$esm$2f$index$2e$esm$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["initializeApp"])(firebaseConfig);
} else {
    app = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$app$2f$dist$2f$esm$2f$index$2e$esm$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getApps"])()[0];
}
const auth = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["getAuth"])(app);
async function signIn(email, password) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["signInWithEmailAndPassword"])(auth, email, password);
}
async function signUp(email, password) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createUserWithEmailAndPassword"])(auth, email, password);
}
async function signOut() {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["signOut"])(auth);
}
async function getIdToken() {
    const user = auth.currentUser;
    if (!user) return null;
    return user.getIdToken();
}
function onAuthChange(callback) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["onAuthStateChanged"])(auth, callback);
}
;
const __TURBOPACK__default__export__ = app;
}),
"[project]/src/types/api.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
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
"[project]/src/lib/api.ts [app-ssr] (ecmascript) <locals>", ((__turbopack_context__) => {
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
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/types/api.ts [app-ssr] (ecmascript)");
;
// API Configuration - uses environment variable only
const API_URL = ("TURBOPACK compile-time value", "https://camelcase-refactor.preview.emergentagent.com/api");
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
    if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]) {
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
    if ("TURBOPACK compile-time falsy", 0) //TURBOPACK unreachable
    ;
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
                const error = new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](errorData.detail || errorData.message || `Request failed with status ${response.status}`, response.status, errorData.errorCode);
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
            if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]) {
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
                    throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](isServerWaking ? 'Server is starting up. Please wait a moment and try again.' : 'Request timeout. Please try again.', 408, 'TIMEOUT');
                }
                throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](error.message || 'Network error', 0, 'NETWORK_ERROR');
            }
            throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Unknown error occurred', 0, 'UNKNOWN');
        }
    }
    throw lastError || new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Request failed after retries', 0, 'RETRY_EXHAUSTED');
}
async function fetchWithAuth(endpoint, token, options = {}) {
    if (!token) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Authentication required', 401, 'AUTH_REQUIRED');
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
    const apiUrl = ("TURBOPACK compile-time value", "https://camelcase-refactor.preview.emergentagent.com/api") || '';
    return fetch(`${apiUrl}/api/admin/inquiries/export?${params.toString()}`, {
        headers: {
            Authorization: `Bearer ${token}`
        }
    }).then((res)=>{
        if (!res.ok) throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Export failed', res.status);
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
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](`Invalid image type for ${context}. Allowed: JPEG, PNG, WEBP`, 400, 'INVALID_IMAGE_TYPE');
    }
    if (file.size > maxSize) {
        const maxMB = (maxSize / (1024 * 1024)).toFixed(1);
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](`Image too large. Maximum size: ${maxMB} MB`, 400, 'IMAGE_TOO_LARGE');
    }
}
async function uploadCategoryImage(token, file) {
    validateImageFile(file, MAX_CATEGORY_IMAGE_SIZE, 'category');
    const { uploadAdminCategoryImage } = await __turbopack_context__.A("[project]/src/lib/cloudinary.ts [app-ssr] (ecmascript, async loader)");
    const result = await uploadAdminCategoryImage(file);
    return {
        imageUrl: result.url
    };
}
async function uploadProductImages(token, files) {
    if (files.length === 0) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('At least one image is required', 400);
    }
    if (files.length > MAX_PRODUCT_IMAGES) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"](`Maximum ${MAX_PRODUCT_IMAGES} images allowed`, 400);
    }
    files.forEach((file, idx)=>{
        validateImageFile(file, MAX_PRODUCT_IMAGE_SIZE, `product image ${idx + 1}`);
    });
    const { uploadSellerProductImage } = await __turbopack_context__.A("[project]/src/lib/cloudinary.ts [app-ssr] (ecmascript, async loader)");
    const uploadPromises = files.map((file)=>uploadSellerProductImage(file));
    const results = await Promise.all(uploadPromises);
    return {
        images: results.map((r)=>r.url)
    };
}
async function uploadProductDatasheet(token, file) {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Only PDF files are allowed for datasheets', 400, 'INVALID_FILE_TYPE');
    }
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
        throw new __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]('Datasheet file must be less than 5MB', 400, 'FILE_TOO_LARGE');
    }
    const { uploadSellerDatasheet } = await __turbopack_context__.A("[project]/src/lib/cloudinary.ts [app-ssr] (ecmascript, async loader)");
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
"[project]/src/lib/api.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ApiError",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"],
    "acceptInquiry",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["acceptInquiry"],
    "activateSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["activateSubscription"],
    "checkHealth",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["checkHealth"],
    "checkReadiness",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["checkReadiness"],
    "createAdminCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAdminCategory"],
    "createAdminProduct",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAdminProduct"],
    "createAdminSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createAdminSpecTemplate"],
    "createB2BCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createB2BCategory"],
    "createB2BSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createB2BSpecTemplate"],
    "createGlobalDropdown",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createGlobalDropdown"],
    "createInquiry",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createInquiry"],
    "createListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createListing"],
    "createSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["createSellerListing"],
    "deleteAccount",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteAccount"],
    "deleteAdminCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteAdminCategory"],
    "deleteAdminProduct",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteAdminProduct"],
    "deleteAdminSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteAdminSpecTemplate"],
    "deleteB2BSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteB2BSpecTemplate"],
    "deleteGlobalDropdown",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteGlobalDropdown"],
    "deleteListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteListing"],
    "deleteSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["deleteSellerListing"],
    "exportAdminInquiries",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["exportAdminInquiries"],
    "extendSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["extendSubscription"],
    "fetchBase",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["fetchBase"],
    "fetchWithAuth",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["fetchWithAuth"],
    "getAdminAnalytics",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminAnalytics"],
    "getAdminCategories",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminCategories"],
    "getAdminInquiries",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminInquiries"],
    "getAdminKPIMetrics",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminKPIMetrics"],
    "getAdminProducts",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminProducts"],
    "getAdminSpecTemplates",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminSpecTemplates"],
    "getAdminStats",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminStats"],
    "getAdminSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminSubscription"],
    "getAdminUsers",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAdminUsers"],
    "getAllCategories",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getAllCategories"],
    "getB2BCategories",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getB2BCategories"],
    "getB2BCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getB2BCategory"],
    "getB2BSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getB2BSpecTemplate"],
    "getB2BSpecTemplates",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getB2BSpecTemplates"],
    "getBuyerInquiries",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getBuyerInquiries"],
    "getCategories",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getCategories"],
    "getCategorySpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getCategorySpecTemplate"],
    "getExpiringSubscriptions",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getExpiringSubscriptions"],
    "getGlobalDropdown",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getGlobalDropdown"],
    "getGlobalDropdowns",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getGlobalDropdowns"],
    "getManufacturers",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getManufacturers"],
    "getMyCategoryRequests",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getMyCategoryRequests"],
    "getMyListings",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getMyListings"],
    "getMyManufacturerRequests",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getMyManufacturerRequests"],
    "getMyProductRequests",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getMyProductRequests"],
    "getMySpecFieldRequests",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getMySpecFieldRequests"],
    "getProduct",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getProduct"],
    "getProductById",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getProductById"],
    "getProductWithSellers",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getProductWithSellers"],
    "getProducts",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getProducts"],
    "getProductsByCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getProductsByCategory"],
    "getPublicCategories",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getPublicCategories"],
    "getSellerDashboard",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerDashboard"],
    "getSellerInquiries",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerInquiries"],
    "getSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerListing"],
    "getSellerListings",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerListings"],
    "getSellerStats",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerStats"],
    "getSellerSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerSubscription"],
    "getSellerSubscriptionStatus",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSellerSubscriptionStatus"],
    "getSpecTemplateById",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getSpecTemplateById"],
    "getUserProfile",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getUserProfile"],
    "pauseSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["pauseSellerListing"],
    "publishListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["publishListing"],
    "publishSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["publishSellerListing"],
    "quickPriceUpdate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["quickPriceUpdate"],
    "reactivateSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["reactivateSubscription"],
    "registerUser",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["registerUser"],
    "rejectInquiry",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["rejectInquiry"],
    "reportInquiry",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["reportInquiry"],
    "requestCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["requestCategory"],
    "requestManufacturer",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["requestManufacturer"],
    "requestProduct",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["requestProduct"],
    "requestSpecField",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["requestSpecField"],
    "restoreUser",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["restoreUser"],
    "runExpiryCheck",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["runExpiryCheck"],
    "sanitizeInput",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["sanitizeInput"],
    "sanitizeObject",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["sanitizeObject"],
    "searchProducts",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["searchProducts"],
    "seedSystemDropdowns",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["seedSystemDropdowns"],
    "suspendSubscription",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["suspendSubscription"],
    "toggleAdminStatus",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["toggleAdminStatus"],
    "updateAdminCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateAdminCategory"],
    "updateAdminProduct",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateAdminProduct"],
    "updateAdminSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateAdminSpecTemplate"],
    "updateB2BCategory",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateB2BCategory"],
    "updateB2BCategorySettings",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateB2BCategorySettings"],
    "updateB2BSpecTemplate",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateB2BSpecTemplate"],
    "updateGlobalDropdown",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateGlobalDropdown"],
    "updateListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateListing"],
    "updateSellerListing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateSellerListing"],
    "updateSellerPricing",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateSellerPricing"],
    "updateUserProfile",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["updateUserProfile"],
    "uploadCategoryImage",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["uploadCategoryImage"],
    "uploadProductDatasheet",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["uploadProductDatasheet"],
    "uploadProductImages",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["uploadProductImages"],
    "waitForBackend",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["waitForBackend"],
    "warmBackend",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["warmBackend"],
    "warmupBackend",
    ()=>__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["warmupBackend"]
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/src/lib/api.ts [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/types/api.ts [app-ssr] (ecmascript)");
}),
"[project]/src/context/AuthContext.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "AuthProvider",
    ()=>AuthProvider,
    "useAuth",
    ()=>useAuth
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$firebase$2f$auth$2f$dist$2f$index$2e$mjs__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/node_modules/firebase/auth/dist/index.mjs [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/@firebase/auth/dist/node-esm/index.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/firebase.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__ = __turbopack_context__.i("[project]/src/lib/api.ts [app-ssr] (ecmascript) <locals>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/types/api.ts [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/api.ts [app-ssr] (ecmascript)");
'use client';
;
;
;
;
;
const AuthContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function AuthProvider({ children }) {
    const [state, setState] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])({
        user: null,
        profile: null,
        loading: true,
        error: null,
        registrationState: 'unknown',
        connectionState: 'connecting',
        connectionMessage: 'Connecting to server...',
        emailVerified: false
    });
    // Warm backend before making auth calls
    const warmupBackend = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useCallback"])(async ()=>{
        setState((prev)=>({
                ...prev,
                connectionState: 'connecting',
                connectionMessage: 'Connecting to server...'
            }));
        const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["warmBackend"])();
        setState((prev)=>({
                ...prev,
                connectionState: result.ready ? 'ready' : 'connecting',
                connectionMessage: result.message
            }));
        return result.ready;
    }, []);
    // Fetch profile helper - never logs tokens
    const fetchProfile = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useCallback"])(async (user)=>{
        try {
            const token = await user.getIdToken();
            return await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$locals$3e$__["getUserProfile"])(token);
        } catch (error) {
            if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"] && error.status === 404) {
                return null;
            }
            if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"] && error.status === 401) {
                return null;
            }
            throw error;
        }
    }, []);
    // Determine registration state
    const determineRegistrationState = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useCallback"])((user, profile)=>{
        if (profile) {
            return 'complete';
        }
        if (!user.emailVerified) {
            return 'email_not_verified';
        }
        return 'incomplete';
    }, []);
    // Initialize auth state listener
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const unsubscribe = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["onAuthStateChanged"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"], async (user)=>{
            if (user) {
                try {
                    await warmupBackend();
                    const profile = await fetchProfile(user);
                    const regState = determineRegistrationState(user, profile);
                    setState((prev)=>({
                            ...prev,
                            user,
                            profile,
                            loading: false,
                            error: null,
                            registrationState: regState,
                            emailVerified: user.emailVerified,
                            connectionState: 'ready',
                            connectionMessage: 'Connected'
                        }));
                } catch (error) {
                    setState((prev)=>({
                            ...prev,
                            user,
                            profile: null,
                            loading: false,
                            error: 'Failed to load profile. Please try again.',
                            registrationState: 'unknown',
                            emailVerified: user.emailVerified,
                            connectionState: 'error',
                            connectionMessage: 'Connection error'
                        }));
                }
            } else {
                setState((prev)=>({
                        ...prev,
                        user: null,
                        profile: null,
                        loading: false,
                        error: null,
                        registrationState: 'unknown',
                        emailVerified: false,
                        connectionState: 'ready',
                        connectionMessage: ''
                    }));
            }
        });
        return ()=>unsubscribe();
    }, [
        fetchProfile,
        warmupBackend,
        determineRegistrationState
    ]);
    // Sign in with email/password
    const signIn = async (email, password)=>{
        setState((prev)=>({
                ...prev,
                loading: true,
                error: null
            }));
        try {
            const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["signInWithEmailAndPassword"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"], email, password);
            if (!result.user.emailVerified) {
                setState((prev)=>({
                        ...prev,
                        user: result.user,
                        profile: null,
                        loading: false,
                        error: null,
                        registrationState: 'email_not_verified',
                        emailVerified: false
                    }));
                return {
                    needsRegistration: false,
                    needsEmailVerification: true
                };
            }
            const profile = await fetchProfile(result.user);
            if (!profile) {
                setState((prev)=>({
                        ...prev,
                        user: result.user,
                        profile: null,
                        loading: false,
                        error: null,
                        registrationState: 'incomplete',
                        emailVerified: true
                    }));
                return {
                    needsRegistration: true,
                    needsEmailVerification: false
                };
            }
            if (profile.accountStatus === 'SUSPENDED') {
                await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["signOut"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"]);
                const error = 'Your account has been suspended. Please contact support.';
                setState((prev)=>({
                        ...prev,
                        loading: false,
                        error
                    }));
                throw new Error(error);
            }
            setState((prev)=>({
                    ...prev,
                    user: result.user,
                    profile,
                    loading: false,
                    error: null,
                    registrationState: 'complete',
                    emailVerified: true
                }));
            return {
                needsRegistration: false,
                needsEmailVerification: false
            };
        } catch (error) {
            if (state.registrationState === 'incomplete') {
                return {
                    needsRegistration: true,
                    needsEmailVerification: false
                };
            }
            if (state.registrationState === 'email_not_verified') {
                return {
                    needsRegistration: false,
                    needsEmailVerification: true
                };
            }
            const message = getAuthErrorMessage(error);
            setState((prev)=>({
                    ...prev,
                    loading: false,
                    error: message,
                    registrationState: 'unknown'
                }));
            throw new Error(message);
        }
    };
    // Sign up - Only create Firebase user, send verification email
    const signUp = async (email, password)=>{
        setState((prev)=>({
                ...prev,
                loading: true,
                error: null
            }));
        try {
            const result = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["createUserWithEmailAndPassword"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"], email, password);
            await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["sendEmailVerification"])(result.user);
            setState((prev)=>({
                    ...prev,
                    user: result.user,
                    profile: null,
                    loading: false,
                    error: null,
                    registrationState: 'email_not_verified',
                    emailVerified: false
                }));
            return {
                needsEmailVerification: true
            };
        } catch (error) {
            const message = getAuthErrorMessage(error);
            setState((prev)=>({
                    ...prev,
                    loading: false,
                    error: message
                }));
            throw new Error(message);
        }
    };
    // Complete registration with role selection
    const completeRegistrationHandler = async (profileData)=>{
        if (!state.user) {
            throw new Error('No user logged in');
        }
        if (!state.user.emailVerified) {
            throw new Error('Email verification required before completing registration');
        }
        setState((prev)=>({
                ...prev,
                loading: true,
                error: null
            }));
        try {
            const token = await state.user.getIdToken();
            const response = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["completeProfile"])(token, profileData);
            setState((prev)=>({
                    ...prev,
                    user: state.user,
                    profile: response.user,
                    loading: false,
                    error: null,
                    registrationState: 'complete',
                    emailVerified: true
                }));
        } catch (error) {
            const message = getAuthErrorMessage(error);
            setState((prev)=>({
                    ...prev,
                    loading: false,
                    error: message
                }));
            throw new Error(message);
        }
    };
    // Resend verification email
    const resendVerificationEmail = async ()=>{
        if (!state.user) {
            throw new Error('No user logged in');
        }
        try {
            await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["sendEmailVerification"])(state.user);
        } catch (error) {
            const message = getAuthErrorMessage(error);
            throw new Error(message);
        }
    };
    // Check if email has been verified
    const checkEmailVerification = async ()=>{
        if (!state.user) {
            return false;
        }
        try {
            await state.user.reload();
            const verified = state.user.emailVerified;
            if (verified && state.registrationState === 'email_not_verified') {
                setState((prev)=>({
                        ...prev,
                        registrationState: 'incomplete',
                        emailVerified: true
                    }));
            }
            return verified;
        } catch  {
            return false;
        }
    };
    // Sign out
    const signOut = async ()=>{
        try {
            await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["signOut"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"]);
        } catch  {
        // Silently handle sign out errors
        }
        setState((prev)=>({
                ...prev,
                user: null,
                profile: null,
                loading: false,
                error: null,
                registrationState: 'unknown',
                emailVerified: false
            }));
    };
    // Reset password
    const resetPassword = async (email)=>{
        try {
            await (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f40$firebase$2f$auth$2f$dist$2f$node$2d$esm$2f$index$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["sendPasswordResetEmail"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$firebase$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["auth"], email);
        } catch (error) {
            const message = getAuthErrorMessage(error);
            throw new Error(message);
        }
    };
    // Get ID token
    const getIdToken = async ()=>{
        if (!state.user) return null;
        try {
            return await state.user.getIdToken();
        } catch  {
            return null;
        }
    };
    // Refresh profile from backend
    const refreshProfile = async ()=>{
        if (!state.user) return;
        try {
            const profile = await fetchProfile(state.user);
            setState((prev)=>({
                    ...prev,
                    profile,
                    registrationState: profile ? 'complete' : state.user?.emailVerified ? 'incomplete' : 'email_not_verified'
                }));
        } catch (error) {
            if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"] && error.isAuthError()) {
                await signOut();
            }
        }
    };
    // Clear error
    const clearError = ()=>{
        setState((prev)=>({
                ...prev,
                error: null
            }));
    };
    // Computed properties
    const isAuthenticated = !!state.user && !!state.profile;
    const isAdmin = state.profile?.isAdmin === true;
    const roles = state.profile?.roles || [];
    const isSeller = roles.includes('seller');
    const isGstVerified = state.profile?.gst?.verified === true;
    const needsRegistration = state.registrationState === 'incomplete';
    const needsEmailVerification = state.registrationState === 'email_not_verified';
    const role = !state.user ? 'guest' : !state.profile ? 'guest' : isAdmin ? 'admin' : isSeller ? 'seller' : 'buyer';
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(AuthContext.Provider, {
        value: {
            ...state,
            isAuthenticated,
            isAdmin,
            isSeller,
            isGstVerified,
            role,
            needsRegistration,
            needsEmailVerification,
            signIn,
            signUp,
            completeRegistration: completeRegistrationHandler,
            signOut,
            resetPassword,
            resendVerificationEmail,
            getIdToken,
            refreshProfile,
            checkEmailVerification,
            clearError
        },
        children: children
    }, void 0, false, {
        fileName: "[project]/src/context/AuthContext.tsx",
        lineNumber: 425,
        columnNumber: 5
    }, this);
}
function useAuth() {
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useContext"])(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
// Helper to get user-friendly auth error messages
function getAuthErrorMessage(error) {
    if (error instanceof __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$types$2f$api$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["ApiError"]) {
        return error.getUserMessage();
    }
    if (error instanceof Error) {
        const errorCode = error.code;
        switch(errorCode){
            case 'auth/user-not-found':
            case 'auth/wrong-password':
            case 'auth/invalid-credential':
                return 'Invalid email or password';
            case 'auth/email-already-in-use':
                return 'This email is already registered';
            case 'auth/weak-password':
                return 'Password must be at least 6 characters';
            case 'auth/invalid-email':
                return 'Please enter a valid email address';
            case 'auth/too-many-requests':
                return 'Too many failed attempts. Please try again later';
            case 'auth/network-request-failed':
                return 'Network error. Please check your connection';
            default:
                return error.message || 'Authentication failed';
        }
    }
    return 'An unexpected error occurred';
}
}),
"[externals]/next/dist/server/app-render/action-async-storage.external.js [external] (next/dist/server/app-render/action-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/action-async-storage.external.js", () => require("next/dist/server/app-render/action-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[project]/src/lib/config.ts [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// Central configuration - Single source of truth for app-wide constants
// Change here = change everywhere
__turbopack_context__.s([
    "APP_DESCRIPTION",
    ()=>APP_DESCRIPTION,
    "APP_KEYWORDS",
    ()=>APP_KEYWORDS,
    "APP_NAME",
    ()=>APP_NAME,
    "APP_TAGLINE",
    ()=>APP_TAGLINE,
    "FOOTER",
    ()=>FOOTER,
    "SEO",
    ()=>SEO
]);
const APP_NAME = "MidConnect";
const APP_TAGLINE = "India's Industrial Marketplace";
const APP_DESCRIPTION = "Connect with verified manufacturers, dealers, and distributors. Buy industrial products - Steel, Electrical, Chemicals, Building Materials and more.";
const APP_KEYWORDS = "B2B marketplace, industrial products, manufacturers, dealers, steel, electrical equipment, chemicals, India";
const SEO = {
    title: `${APP_NAME} - ${APP_TAGLINE}`,
    description: APP_DESCRIPTION,
    keywords: APP_KEYWORDS,
    ogTitle: `${APP_NAME} - ${APP_TAGLINE}`,
    ogDescription: "Connect with verified manufacturers, dealers, and distributors.",
    twitterCard: "summary"
};
const FOOTER = {
    tagline: "India's trusted B2B marketplace for industrial products. Connect with verified manufacturers, dealers, and distributors.",
    copyright: (year)=>`© ${year} ${APP_NAME}. All rights reserved.`
};
}),
"[project]/src/components/Header.tsx [app-ssr] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "default",
    ()=>Header
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/client/app-dir/link.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$context$2f$AuthContext$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/context/AuthContext.tsx [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/search.js [app-ssr] (ecmascript) <export default as Search>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$menu$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Menu$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/menu.js [app-ssr] (ecmascript) <export default as Menu>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/x.js [app-ssr] (ecmascript) <export default as X>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$user$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__User$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/user.js [app-ssr] (ecmascript) <export default as User>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$log$2d$out$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__LogOut$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/log-out.js [app-ssr] (ecmascript) <export default as LogOut>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shopping$2d$bag$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__ShoppingBag$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/shopping-bag.js [app-ssr] (ecmascript) <export default as ShoppingBag>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$settings$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Settings$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/settings.js [app-ssr] (ecmascript) <export default as Settings>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$package$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Package$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/package.js [app-ssr] (ecmascript) <export default as Package>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/chevron-down.js [app-ssr] (ecmascript) <export default as ChevronDown>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$layout$2d$dashboard$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__LayoutDashboard$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/layout-dashboard.js [app-ssr] (ecmascript) <export default as LayoutDashboard>");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$config$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/config.ts [app-ssr] (ecmascript)");
'use client';
;
;
;
;
;
;
;
function Header() {
    const { user, profile, signOut, loading, isAdmin, isSeller, role } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$context$2f$AuthContext$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useAuth"])();
    const [isMenuOpen, setIsMenuOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    const [isUserMenuOpen, setIsUserMenuOpen] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])(false);
    const [searchQuery, setSearchQuery] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useState"])('');
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRouter"])();
    const handleSearch = (e)=>{
        e.preventDefault();
        const sanitizedQuery = searchQuery.trim().slice(0, 100);
        if (sanitizedQuery) {
            router.push(`/search?q=${encodeURIComponent(sanitizedQuery)}`);
            setSearchQuery('');
        }
    };
    const handleSignOut = async ()=>{
        await signOut();
        setIsUserMenuOpen(false);
        router.push('/');
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("header", {
        className: "bg-white shadow-sm sticky top-0 z-50",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex items-center justify-between h-16",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                href: "/",
                                className: "flex items-center gap-2",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$shopping$2d$bag$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__ShoppingBag$3e$__["ShoppingBag"], {
                                        className: "h-8 w-8 text-blue-600"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 38,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "text-xl font-bold text-gray-900",
                                        children: __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$config$2e$ts__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["APP_NAME"]
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 39,
                                        columnNumber: 13
                                    }, this)
                                ]
                            }, void 0, true, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 37,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                                onSubmit: handleSearch,
                                className: "hidden md:flex flex-1 max-w-lg mx-8",
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "relative w-full",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "text",
                                            placeholder: "Search products, categories...",
                                            value: searchQuery,
                                            onChange: (e)=>setSearchQuery(e.target.value),
                                            maxLength: 100,
                                            className: "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        }, void 0, false, {
                                            fileName: "[project]/src/components/Header.tsx",
                                            lineNumber: 45,
                                            columnNumber: 15
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__["Search"], {
                                            className: "absolute left-3 top-2.5 h-5 w-5 text-gray-400"
                                        }, void 0, false, {
                                            fileName: "[project]/src/components/Header.tsx",
                                            lineNumber: 53,
                                            columnNumber: 15
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/src/components/Header.tsx",
                                    lineNumber: 44,
                                    columnNumber: 13
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 43,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                                className: "hidden md:flex items-center gap-6",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/products",
                                        className: "text-gray-600 hover:text-gray-900",
                                        children: "Products"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 59,
                                        columnNumber: 13
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/categories",
                                        className: "text-gray-600 hover:text-gray-900",
                                        children: "Categories"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 60,
                                        columnNumber: 13
                                    }, this),
                                    !loading && (user ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "relative",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                onClick: ()=>setIsUserMenuOpen(!isUserMenuOpen),
                                                className: "flex items-center gap-2 text-gray-600 hover:text-gray-900",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        className: "w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center",
                                                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$user$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__User$3e$__["User"], {
                                                            className: "h-4 w-4 text-blue-600"
                                                        }, void 0, false, {
                                                            fileName: "[project]/src/components/Header.tsx",
                                                            lineNumber: 70,
                                                            columnNumber: 23
                                                        }, this)
                                                    }, void 0, false, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 69,
                                                        columnNumber: 21
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                        className: "text-sm max-w-[120px] truncate",
                                                        children: profile?.businessName || user.email?.split('@')[0]
                                                    }, void 0, false, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 72,
                                                        columnNumber: 21
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chevron$2d$down$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__ChevronDown$3e$__["ChevronDown"], {
                                                        className: "h-4 w-4"
                                                    }, void 0, false, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 75,
                                                        columnNumber: 21
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 65,
                                                columnNumber: 19
                                            }, this),
                                            isUserMenuOpen && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                className: "absolute right-0 top-full mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-100 py-2 z-50",
                                                children: [
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                                        className: "px-4 py-2 border-b border-gray-100",
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                                className: "text-sm font-medium text-gray-900 truncate",
                                                                children: profile?.businessName || 'User'
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 82,
                                                                columnNumber: 25
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                                                className: "text-xs text-gray-500 truncate",
                                                                children: user.email
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 85,
                                                                columnNumber: 25
                                                            }, this),
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                                                className: `inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${isAdmin ? 'bg-purple-100 text-purple-700' : isSeller ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`,
                                                                children: isAdmin ? 'Admin' : isSeller ? 'Seller' : 'Buyer'
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 86,
                                                                columnNumber: 25
                                                            }, this)
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 81,
                                                        columnNumber: 23
                                                    }, this),
                                                    isAdmin && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                        href: "/admin",
                                                        className: "flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50",
                                                        onClick: ()=>setIsUserMenuOpen(false),
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$settings$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Settings$3e$__["Settings"], {
                                                                className: "h-4 w-4"
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 102,
                                                                columnNumber: 27
                                                            }, this),
                                                            " Admin Panel"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 97,
                                                        columnNumber: 25
                                                    }, this),
                                                    isSeller && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                        href: "/seller",
                                                        className: "flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50",
                                                        onClick: ()=>setIsUserMenuOpen(false),
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$layout$2d$dashboard$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__LayoutDashboard$3e$__["LayoutDashboard"], {
                                                                className: "h-4 w-4"
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 112,
                                                                columnNumber: 27
                                                            }, this),
                                                            " Seller Dashboard"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 107,
                                                        columnNumber: 25
                                                    }, this),
                                                    isSeller && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                        href: "/seller/listings",
                                                        className: "flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50",
                                                        onClick: ()=>setIsUserMenuOpen(false),
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$package$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Package$3e$__["Package"], {
                                                                className: "h-4 w-4"
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 122,
                                                                columnNumber: 27
                                                            }, this),
                                                            " My Listings"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 117,
                                                        columnNumber: 25
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                        href: "/seller/profile",
                                                        className: "flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50",
                                                        onClick: ()=>setIsUserMenuOpen(false),
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$user$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__User$3e$__["User"], {
                                                                className: "h-4 w-4"
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 131,
                                                                columnNumber: 25
                                                            }, this),
                                                            " Profile"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 126,
                                                        columnNumber: 23
                                                    }, this),
                                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                        onClick: handleSignOut,
                                                        className: "flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full",
                                                        children: [
                                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$log$2d$out$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__LogOut$3e$__["LogOut"], {
                                                                className: "h-4 w-4"
                                                            }, void 0, false, {
                                                                fileName: "[project]/src/components/Header.tsx",
                                                                lineNumber: 138,
                                                                columnNumber: 25
                                                            }, this),
                                                            " Sign Out"
                                                        ]
                                                    }, void 0, true, {
                                                        fileName: "[project]/src/components/Header.tsx",
                                                        lineNumber: 134,
                                                        columnNumber: 23
                                                    }, this)
                                                ]
                                            }, void 0, true, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 80,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 64,
                                        columnNumber: 17
                                    }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                        className: "flex items-center gap-3",
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/login",
                                                className: "text-gray-600 hover:text-gray-900",
                                                children: "Login"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 145,
                                                columnNumber: 19
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/register",
                                                className: "bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700",
                                                children: "Sign Up"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 151,
                                                columnNumber: 19
                                            }, this)
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 144,
                                        columnNumber: 17
                                    }, this))
                                ]
                            }, void 0, true, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 58,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                className: "md:hidden p-2",
                                onClick: ()=>setIsMenuOpen(!isMenuOpen),
                                "aria-label": isMenuOpen ? 'Close menu' : 'Open menu',
                                children: isMenuOpen ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$x$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__X$3e$__["X"], {
                                    className: "h-6 w-6"
                                }, void 0, false, {
                                    fileName: "[project]/src/components/Header.tsx",
                                    lineNumber: 168,
                                    columnNumber: 27
                                }, this) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$menu$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Menu$3e$__["Menu"], {
                                    className: "h-6 w-6"
                                }, void 0, false, {
                                    fileName: "[project]/src/components/Header.tsx",
                                    lineNumber: 168,
                                    columnNumber: 55
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 163,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/src/components/Header.tsx",
                        lineNumber: 35,
                        columnNumber: 9
                    }, this),
                    isMenuOpen && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "md:hidden py-4 border-t",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("form", {
                                onSubmit: handleSearch,
                                className: "mb-4",
                                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                    className: "relative",
                                    children: [
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("input", {
                                            type: "text",
                                            placeholder: "Search products...",
                                            value: searchQuery,
                                            onChange: (e)=>setSearchQuery(e.target.value),
                                            maxLength: 100,
                                            className: "w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg"
                                        }, void 0, false, {
                                            fileName: "[project]/src/components/Header.tsx",
                                            lineNumber: 177,
                                            columnNumber: 17
                                        }, this),
                                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$search$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__$3c$export__default__as__Search$3e$__["Search"], {
                                            className: "absolute left-3 top-2.5 h-5 w-5 text-gray-400"
                                        }, void 0, false, {
                                            fileName: "[project]/src/components/Header.tsx",
                                            lineNumber: 185,
                                            columnNumber: 17
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/src/components/Header.tsx",
                                    lineNumber: 176,
                                    columnNumber: 15
                                }, this)
                            }, void 0, false, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 175,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                                className: "flex flex-col gap-4",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/products",
                                        className: "text-gray-600",
                                        onClick: ()=>setIsMenuOpen(false),
                                        children: "Products"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 189,
                                        columnNumber: 15
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                        href: "/categories",
                                        className: "text-gray-600",
                                        onClick: ()=>setIsMenuOpen(false),
                                        children: "Categories"
                                    }, void 0, false, {
                                        fileName: "[project]/src/components/Header.tsx",
                                        lineNumber: 190,
                                        columnNumber: 15
                                    }, this),
                                    !loading && (user ? /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            isAdmin && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/admin",
                                                className: "text-gray-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "Admin Panel"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 196,
                                                columnNumber: 23
                                            }, this),
                                            isSeller && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/seller",
                                                className: "text-gray-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "Seller Dashboard"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 201,
                                                columnNumber: 23
                                            }, this),
                                            isSeller && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/seller/listings",
                                                className: "text-gray-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "My Listings"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 206,
                                                columnNumber: 23
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/seller/profile",
                                                className: "text-gray-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "Profile"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 210,
                                                columnNumber: 21
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                                onClick: handleSignOut,
                                                className: "text-left text-red-600",
                                                children: "Sign Out"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 213,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, void 0, true) : /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["Fragment"], {
                                        children: [
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/login",
                                                className: "text-blue-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "Login"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 219,
                                                columnNumber: 21
                                            }, this),
                                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"], {
                                                href: "/register",
                                                className: "text-blue-600",
                                                onClick: ()=>setIsMenuOpen(false),
                                                children: "Sign Up"
                                            }, void 0, false, {
                                                fileName: "[project]/src/components/Header.tsx",
                                                lineNumber: 220,
                                                columnNumber: 21
                                            }, this)
                                        ]
                                    }, void 0, true))
                                ]
                            }, void 0, true, {
                                fileName: "[project]/src/components/Header.tsx",
                                lineNumber: 188,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/src/components/Header.tsx",
                        lineNumber: 174,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/src/components/Header.tsx",
                lineNumber: 34,
                columnNumber: 7
            }, this),
            isUserMenuOpen && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "fixed inset-0 z-40",
                onClick: ()=>setIsUserMenuOpen(false)
            }, void 0, false, {
                fileName: "[project]/src/components/Header.tsx",
                lineNumber: 231,
                columnNumber: 9
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/src/components/Header.tsx",
        lineNumber: 33,
        columnNumber: 5
    }, this);
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__61c99f59._.js.map