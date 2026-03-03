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
 */

// Cloudinary Configuration
const CLOUDINARY_CLOUD_NAME = process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME || 'dco24qmoq';
const CLOUDINARY_IMAGE_URL = `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`;
const CLOUDINARY_VIDEO_URL = `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/video/upload`;
const CLOUDINARY_RAW_URL = `https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/raw/upload`;

// Upload Presets (MUST MATCH EXACTLY)
export const UPLOAD_PRESETS = {
  adminProductImage: 'midconnect_admin_product_upload',
  adminCategoryImage: 'midconnect_admin_category_upload',
  sellerProductImage: 'midconnect_seller_product_upload',
  sellerProductVideo: 'midconnect_seller_product_upload',  // Videos use same preset
  sellerDatasheet: 'midconnect_seller_datasheet_upload',
} as const;

export type UploadType = keyof typeof UPLOAD_PRESETS;

// Validation Configuration
const IMAGE_MAX_SIZE = 2 * 1024 * 1024; // 2MB
const VIDEO_MAX_SIZE = 5 * 1024 * 1024; // 5MB
const PDF_MAX_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime'];
const ALLOWED_PDF_TYPES = ['application/pdf'];

// Compression Configuration
const COMPRESSION_QUALITY = 0.8;
const MAX_IMAGE_WIDTH = 1920;

export interface UploadProgress {
  progress: number;
  bytesTransferred: number;
  totalBytes: number;
}

export interface UploadResult {
  url: string;
  publicId: string;
  format: string;
  width?: number;
  height?: number;
}

export class CloudinaryError extends Error {
  constructor(
    message: string,
    public code: string
  ) {
    super(message);
    this.name = 'CloudinaryError';
  }
}

/**
 * Validate file before upload
 */
export function validateFile(file: File, type: UploadType): void {
  const isPdf = type === 'sellerDatasheet';
  const isVideo = type === 'sellerProductVideo';
  
  let allowedTypes: string[];
  let maxSize: number;
  
  if (isPdf) {
    allowedTypes = ALLOWED_PDF_TYPES;
    maxSize = PDF_MAX_SIZE;
  } else if (isVideo) {
    allowedTypes = ALLOWED_VIDEO_TYPES;
    maxSize = VIDEO_MAX_SIZE;
  } else {
    allowedTypes = ALLOWED_IMAGE_TYPES;
    maxSize = IMAGE_MAX_SIZE;
  }
  
  const maxSizeMB = maxSize / (1024 * 1024);

  // Check file type
  if (!allowedTypes.includes(file.type)) {
    let formats: string;
    if (isPdf) formats = 'PDF';
    else if (isVideo) formats = 'MP4, WebM, MOV';
    else formats = 'JPEG, PNG, WEBP';
    
    throw new CloudinaryError(
      `Invalid file type. Allowed formats: ${formats}`,
      'INVALID_TYPE'
    );
  }

  // Check file size
  if (file.size > maxSize) {
    throw new CloudinaryError(
      `File too large. Maximum size: ${maxSizeMB}MB`,
      'FILE_TOO_LARGE'
    );
  }

  // Check for empty file
  if (file.size === 0) {
    throw new CloudinaryError('File is empty', 'EMPTY_FILE');
  }
}

/**
 * Compress image before upload
 * - Resize to max 1920px width
 * - Reduce quality to 0.8
 * - Convert to JPEG for better compression
 */
export async function compressImage(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      reject(new CloudinaryError('Canvas not supported', 'CANVAS_ERROR'));
      return;
    }

    img.onload = () => {
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
      canvas.toBlob(
        (blob) => {
          if (blob) {
            // Check if compressed size is still under limit
            if (blob.size > IMAGE_MAX_SIZE) {
              // Try lower quality
              canvas.toBlob(
                (lowerQualityBlob) => {
                  if (lowerQualityBlob && lowerQualityBlob.size <= IMAGE_MAX_SIZE) {
                    resolve(lowerQualityBlob);
                  } else {
                    // Return original if compression doesn't help enough
                    resolve(blob);
                  }
                },
                'image/jpeg',
                0.6
              );
            } else {
              resolve(blob);
            }
          } else {
            reject(new CloudinaryError('Compression failed', 'COMPRESSION_ERROR'));
          }
        },
        'image/jpeg',
        COMPRESSION_QUALITY
      );
    };

    img.onerror = () => {
      reject(new CloudinaryError('Failed to load image', 'IMAGE_LOAD_ERROR'));
    };

    // Load image from file
    const reader = new FileReader();
    reader.onload = (e) => {
      img.src = e.target?.result as string;
    };
    reader.onerror = () => {
      reject(new CloudinaryError('Failed to read file', 'FILE_READ_ERROR'));
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Optimize Cloudinary image URL with f_auto, q_auto
 */
export function optimizeImageUrl(url: string): string {
  if (!url.includes('res.cloudinary.com')) return url;
  
  // Don't optimize raw (PDF) URLs
  if (url.includes('/raw/upload/')) return url;
  
  // Add optimization parameters
  return url.replace('/upload/', '/upload/f_auto,q_auto/');
}

/**
 * Optimize Cloudinary video URL with auto compression
 */
export function optimizeVideoUrl(url: string): string {
  if (!url.includes('res.cloudinary.com')) return url;
  
  // Don't optimize raw URLs
  if (url.includes('/raw/upload/')) return url;
  
  // Add video optimization parameters (quality auto, format auto, video codec auto)
  return url.replace('/upload/', '/upload/q_auto,f_auto,vc_auto/');
}

/**
 * Upload file to Cloudinary
 * 
 * @param file - File to upload
 * @param type - Upload type (determines preset and endpoint)
 * @param onProgress - Optional progress callback
 * @returns Upload result with optimized URL
 */
export async function uploadToCloudinary(
  file: File,
  type: UploadType,
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadResult> {
  // Validate file
  validateFile(file, type);

  const isPdf = type === 'sellerDatasheet';
  const isVideo = type === 'sellerProductVideo';
  const preset = UPLOAD_PRESETS[type];
  
  // Determine upload endpoint
  let uploadUrl: string;
  if (isPdf) {
    uploadUrl = CLOUDINARY_RAW_URL;
  } else if (isVideo) {
    uploadUrl = CLOUDINARY_VIDEO_URL;
  } else {
    uploadUrl = CLOUDINARY_IMAGE_URL;
  }

  // Compress image if not PDF or video
  let fileToUpload: File | Blob = file;
  if (!isPdf && !isVideo) {
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
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress({
          progress: (event.loaded / event.total) * 100,
          bytesTransferred: event.loaded,
          totalBytes: event.total,
        });
      }
    });

    // Handle completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          
          // Get the secure URL
          let url = response.secure_url;
          
          // Optimize URLs based on type
          if (isVideo) {
            url = optimizeVideoUrl(url);
          } else if (!isPdf) {
            url = optimizeImageUrl(url);
          }

          resolve({
            url,
            publicId: response.public_id,
            format: response.format,
            width: response.width,
            height: response.height,
          });
        } catch (err) {
          reject(new CloudinaryError('Failed to parse response', 'PARSE_ERROR'));
        }
      } else {
        let errorMessage = 'Upload failed';
        try {
          const errorResponse = JSON.parse(xhr.responseText);
          errorMessage = errorResponse.error?.message || errorMessage;
        } catch {
          // Use default error message
        }
        reject(new CloudinaryError(errorMessage, 'UPLOAD_ERROR'));
      }
    });

    // Handle errors
    xhr.addEventListener('error', () => {
      reject(new CloudinaryError('Network error during upload', 'NETWORK_ERROR'));
    });

    xhr.addEventListener('abort', () => {
      reject(new CloudinaryError('Upload cancelled', 'CANCELLED'));
    });

    // Send request
    xhr.open('POST', uploadUrl);
    xhr.send(formData);
  });
}

/**
 * Validate that a URL is from our Cloudinary account
 */
export function isValidCloudinaryUrl(url: string): boolean {
  return url.startsWith(`https://res.cloudinary.com/${CLOUDINARY_CLOUD_NAME}/`);
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Convenience functions for each upload type
export const uploadAdminProductImage = (
  file: File, 
  onProgress?: (progress: UploadProgress) => void
) => uploadToCloudinary(file, 'adminProductImage', onProgress);

export const uploadAdminCategoryImage = (
  file: File, 
  onProgress?: (progress: UploadProgress) => void
) => uploadToCloudinary(file, 'adminCategoryImage', onProgress);

export const uploadSellerProductImage = (
  file: File, 
  onProgress?: (progress: UploadProgress) => void
) => uploadToCloudinary(file, 'sellerProductImage', onProgress);

export const uploadSellerDatasheet = (
  file: File, 
  onProgress?: (progress: UploadProgress) => void
) => uploadToCloudinary(file, 'sellerDatasheet', onProgress);

export const uploadSellerProductVideo = (
  file: File, 
  onProgress?: (progress: UploadProgress) => void
) => uploadToCloudinary(file, 'sellerProductVideo', onProgress);
