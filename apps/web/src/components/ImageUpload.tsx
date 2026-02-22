'use client';

import { useState, useRef, useCallback } from 'react';
import { Upload, X, Image as ImageIcon, AlertCircle, Loader2 } from 'lucide-react';

// Allowed image types
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const ALLOWED_EXTENSIONS = '.jpg,.jpeg,.png,.webp';

interface ImageUploadProps {
  onUpload: (files: File[]) => Promise<string[]>;
  maxFiles?: number;
  maxSizeMB?: number;
  currentImages?: string[];
  onRemove?: (index: number) => void;
  label?: string;
  hint?: string;
  disabled?: boolean;
  className?: string;
}

export default function ImageUpload({
  onUpload,
  maxFiles = 1,
  maxSizeMB = 2,
  currentImages = [],
  onRemove,
  label = 'Upload Image',
  hint,
  disabled = false,
  className = '',
}: ImageUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  const canAddMore = currentImages.length < maxFiles;

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `Invalid file type: ${file.name}. Only JPEG, PNG, and WEBP are allowed.`;
    }
    if (file.size > maxSizeBytes) {
      return `File too large: ${file.name}. Maximum size is ${maxSizeMB}MB.`;
    }
    return null;
  };

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    setError(null);
    
    const fileArray = Array.from(files);
    
    // Check how many we can add
    const availableSlots = maxFiles - currentImages.length;
    if (fileArray.length > availableSlots) {
      setError(`Can only add ${availableSlots} more image(s). Maximum ${maxFiles} allowed.`);
      return;
    }

    // Validate all files
    for (const file of fileArray) {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
    }

    // Upload
    setIsUploading(true);
    try {
      await onUpload(fileArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload image');
    } finally {
      setIsUploading(false);
    }
  }, [maxFiles, currentImages.length, maxSizeBytes, onUpload]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (disabled || !canAddMore) return;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [disabled, canAddMore, handleFiles]);

  const handleClick = () => {
    if (!disabled && canAddMore) {
      fileInputRef.current?.click();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  };

  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}

      {/* Error message */}
      {error && (
        <div className="mb-3 bg-red-50 border border-red-200 text-red-600 px-3 py-2 rounded-lg text-sm flex items-start gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Current images */}
      {currentImages.length > 0 && (
        <div className="flex flex-wrap gap-3 mb-3">
          {currentImages.map((img, index) => (
            <div key={index} className="relative group">
              <img
                src={img}
                alt={`Uploaded ${index + 1}`}
                className="w-24 h-24 object-cover rounded-lg border border-gray-200"
              />
              {onRemove && (
                <button
                  type="button"
                  onClick={() => onRemove(index)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label="Remove image"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload area */}
      {canAddMore && (
        <div
          onClick={handleClick}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`
            border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
            ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
            ${disabled || isUploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_EXTENSIONS}
            multiple={maxFiles > 1}
            onChange={handleInputChange}
            className="hidden"
            disabled={disabled || isUploading}
          />

          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="h-10 w-10 text-blue-500 animate-spin mb-2" />
              <p className="text-sm text-gray-600">Uploading...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
                <Upload className="h-6 w-6 text-gray-400" />
              </div>
              <p className="text-sm text-gray-600 mb-1">
                <span className="text-blue-600 font-medium">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-400">
                JPEG, PNG, or WEBP (max {maxSizeMB}MB)
              </p>
              {maxFiles > 1 && (
                <p className="text-xs text-gray-400 mt-1">
                  {currentImages.length}/{maxFiles} images
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Hint text */}
      {hint && (
        <p className="text-xs text-gray-500 mt-2">{hint}</p>
      )}
    </div>
  );
}
