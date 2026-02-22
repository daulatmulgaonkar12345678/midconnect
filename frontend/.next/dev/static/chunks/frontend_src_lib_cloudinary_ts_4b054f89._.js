(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/frontend/src/lib/cloudinary.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "CloudinaryError",
    ()=>CloudinaryError,
    "UPLOAD_PRESETS",
    ()=>UPLOAD_PRESETS,
    "compressImage",
    ()=>compressImage,
    "formatBytes",
    ()=>formatBytes,
    "isValidCloudinaryUrl",
    ()=>isValidCloudinaryUrl,
    "optimizeImageUrl",
    ()=>optimizeImageUrl,
    "uploadAdminCategoryImage",
    ()=>uploadAdminCategoryImage,
    "uploadAdminProductImage",
    ()=>uploadAdminProductImage,
    "uploadSellerDatasheet",
    ()=>uploadSellerDatasheet,
    "uploadSellerProductImage",
    ()=>uploadSellerProductImage,
    "uploadToCloudinary",
    ()=>uploadToCloudinary,
    "validateFile",
    ()=>validateFile
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/frontend/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
/**
 * Cloudinary Upload Utilities for B2B Marketplace
 * 
 * Supports:
 * - adminProductImage: Admin product cover images
 * - adminCategoryImage: Admin category images
 * - sellerProductImage: Seller listing images
 * - sellerDatasheet: Seller PDF datasheets
 * 
 * Features:
 * - Client-side validation (type, size)
 * - Image compression before upload
 * - Cloudinary unsigned upload with presets
 * - URL optimization (f_auto, q_auto)
 */ // Cloudinary Configuration
const CLOUDINARY_CLOUD_NAME = __TURBOPACK__imported__module__$5b$project$5d2f$frontend$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME || 'dco24qmoq';
const CLOUDINARY_IMAGE_URL = `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`;
const CLOUDINARY_RAW_URL = `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/raw/upload`;
const UPLOAD_PRESETS = {
    adminProductImage: 'midconnect_admin_product_upload',
    adminCategoryImage: 'midconnect_admin_category_upload',
    sellerProductImage: 'midconnect_seller_product_upload',
    sellerDatasheet: 'midconnect_seller_datasheet_upload'
};
// Validation Configuration
const IMAGE_MAX_SIZE = 2 * 1024 * 1024; // 2MB
const PDF_MAX_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_IMAGE_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp'
];
const ALLOWED_PDF_TYPES = [
    'application/pdf'
];
// Compression Configuration
const COMPRESSION_QUALITY = 0.8;
const MAX_IMAGE_WIDTH = 1920;
class CloudinaryError extends Error {
    code;
    constructor(message, code){
        super(message), this.code = code;
        this.name = 'CloudinaryError';
    }
}
function validateFile(file, type) {
    const isPdf = type === 'sellerDatasheet';
    const allowedTypes = isPdf ? ALLOWED_PDF_TYPES : ALLOWED_IMAGE_TYPES;
    const maxSize = isPdf ? PDF_MAX_SIZE : IMAGE_MAX_SIZE;
    const maxSizeMB = maxSize / (1024 * 1024);
    // Check file type
    if (!allowedTypes.includes(file.type)) {
        const formats = isPdf ? 'PDF' : 'JPEG, PNG, WEBP';
        throw new CloudinaryError(`Invalid file type. Allowed formats: ${formats}`, 'INVALID_TYPE');
    }
    // Check file size
    if (file.size > maxSize) {
        throw new CloudinaryError(`File too large. Maximum size: ${maxSizeMB}MB`, 'FILE_TOO_LARGE');
    }
    // Check for empty file
    if (file.size === 0) {
        throw new CloudinaryError('File is empty', 'EMPTY_FILE');
    }
}
async function compressImage(file) {
    return new Promise((resolve, reject)=>{
        const img = new Image();
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            reject(new CloudinaryError('Canvas not supported', 'CANVAS_ERROR'));
            return;
        }
        img.onload = ()=>{
            // Calculate new dimensions
            let { width, height } = img;
            if (width > MAX_IMAGE_WIDTH) {
                const ratio = MAX_IMAGE_WIDTH / width;
                width = MAX_IMAGE_WIDTH;
                height = Math.round(height * ratio);
            }
            // Set canvas dimensions
            canvas.width = width;
            canvas.height = height;
            // Draw image
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0, width, height);
            // Convert to blob
            canvas.toBlob((blob)=>{
                if (blob) {
                    // Check if compressed size is still under limit
                    if (blob.size > IMAGE_MAX_SIZE) {
                        // Try lower quality
                        canvas.toBlob((lowerQualityBlob)=>{
                            if (lowerQualityBlob && lowerQualityBlob.size <= IMAGE_MAX_SIZE) {
                                resolve(lowerQualityBlob);
                            } else {
                                // Return original if compression doesn't help enough
                                resolve(blob);
                            }
                        }, 'image/jpeg', 0.6);
                    } else {
                        resolve(blob);
                    }
                } else {
                    reject(new CloudinaryError('Compression failed', 'COMPRESSION_ERROR'));
                }
            }, 'image/jpeg', COMPRESSION_QUALITY);
        };
        img.onerror = ()=>{
            reject(new CloudinaryError('Failed to load image', 'IMAGE_LOAD_ERROR'));
        };
        // Load image from file
        const reader = new FileReader();
        reader.onload = (e)=>{
            img.src = e.target?.result;
        };
        reader.onerror = ()=>{
            reject(new CloudinaryError('Failed to read file', 'FILE_READ_ERROR'));
        };
        reader.readAsDataURL(file);
    });
}
function optimizeImageUrl(url) {
    if (!url.includes('res.cloudinary.com')) return url;
    // Don't optimize raw (PDF) URLs
    if (url.includes('/raw/upload/')) return url;
    // Add optimization parameters
    return url.replace('/upload/', '/upload/f_auto,q_auto/');
}
async function uploadToCloudinary(file, type, onProgress) {
    // Validate file
    validateFile(file, type);
    const isPdf = type === 'sellerDatasheet';
    const preset = UPLOAD_PRESETS[type];
    const uploadUrl = isPdf ? CLOUDINARY_RAW_URL : CLOUDINARY_IMAGE_URL;
    // Compress image if not PDF
    let fileToUpload = file;
    if (!isPdf) {
        try {
            fileToUpload = await compressImage(file);
        } catch (err) {
            console.warn('Image compression failed, using original:', err);
        // Continue with original file
        }
    }
    // Prepare form data
    const formData = new FormData();
    formData.append('file', fileToUpload);
    formData.append('upload_preset', preset);
    // Upload with XMLHttpRequest for progress tracking
    return new Promise((resolve, reject)=>{
        const xhr = new XMLHttpRequest();
        // Track upload progress
        xhr.upload.addEventListener('progress', (event)=>{
            if (event.lengthComputable && onProgress) {
                onProgress({
                    progress: event.loaded / event.total * 100,
                    bytesTransferred: event.loaded,
                    totalBytes: event.total
                });
            }
        });
        // Handle completion
        xhr.addEventListener('load', ()=>{
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    // Get the secure URL
                    let url = response.secure_url;
                    // Optimize image URLs
                    if (!isPdf) {
                        url = optimizeImageUrl(url);
                    }
                    resolve({
                        url,
                        publicId: response.public_id,
                        format: response.format,
                        width: response.width,
                        height: response.height
                    });
                } catch (err) {
                    reject(new CloudinaryError('Failed to parse response', 'PARSE_ERROR'));
                }
            } else {
                let errorMessage = 'Upload failed';
                try {
                    const errorResponse = JSON.parse(xhr.responseText);
                    errorMessage = errorResponse.error?.message || errorMessage;
                } catch  {
                // Use default error message
                }
                reject(new CloudinaryError(errorMessage, 'UPLOAD_ERROR'));
            }
        });
        // Handle errors
        xhr.addEventListener('error', ()=>{
            reject(new CloudinaryError('Network error during upload', 'NETWORK_ERROR'));
        });
        xhr.addEventListener('abort', ()=>{
            reject(new CloudinaryError('Upload cancelled', 'CANCELLED'));
        });
        // Send request
        xhr.open('POST', uploadUrl);
        xhr.send(formData);
    });
}
function isValidCloudinaryUrl(url) {
    return url.startsWith(`https://res.cloudinary.com/${CLOUDINARY_CLOUD_NAME}/`);
}
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = [
        'Bytes',
        'KB',
        'MB',
        'GB'
    ];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
const uploadAdminProductImage = (file, onProgress)=>uploadToCloudinary(file, 'adminProductImage', onProgress);
const uploadAdminCategoryImage = (file, onProgress)=>uploadToCloudinary(file, 'adminCategoryImage', onProgress);
const uploadSellerProductImage = (file, onProgress)=>uploadToCloudinary(file, 'sellerProductImage', onProgress);
const uploadSellerDatasheet = (file, onProgress)=>uploadToCloudinary(file, 'sellerDatasheet', onProgress);
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=frontend_src_lib_cloudinary_ts_4b054f89._.js.map