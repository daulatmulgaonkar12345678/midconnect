'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getSellerListing,
  getCategorySpecTemplate,
  updateSellerListing,
  updateSellerPricing,
  publishSellerListing,
  uploadProductImages,
  uploadProductVideos,
  uploadProductDatasheet
} from '@/lib/api';
import type { SellerListing, B2BSpecTemplate, PricingTier } from '@/types';
import { 
  ArrowLeft, 
  ChevronRight, 
  Loader2, 
  AlertCircle, 
  Check, 
  Package,
  Plus,
  Info,
  Upload,
  X,
  DollarSign,
  Layers,
  FileText,
  Clock,
  HelpCircle,
  Save,
  AlertTriangle,
  Video,
  Play
} from 'lucide-react';
import Link from 'next/link';

// ==================== Types ====================

interface AttributeFieldValue {
  value: string | number | boolean;
  touched: boolean;
}

interface FormState {
  // Step 1: Product Selection (READ-ONLY for edit)
  categoryId: string;
  categoryName: string;
  productId: string;
  productName: string;
  sellerType: string;
  
  // Step 2: Attributes (ProductVariant data)
  attributes: Record<string, AttributeFieldValue>;
  description: string;
  
  // Step 3: Commercial Terms - STRICT camelCase
  moq: number;
  stock: number;
  maxCapacity: number | null;
  leadTime: number | null;
  
  // Pricing - STRICT camelCase with PricingTier model
  pricingType: 'fixed' | 'negotiable' | 'rfq_only';
  pricingTiers: PricingTier[];
  
  // Images & Videos
  images: string[];
  videos: string[];  // Max 2 videos, 30 seconds each
  datasheetUrl: string;
  
  // Status
  status: 'draft' | 'active' | 'paused' | 'archived';
}

// ==================== Unsaved Changes Warning Modal ====================

function UnsavedChangesModal({ 
  onStay, 
  onLeave 
}: { 
  onStay: () => void; 
  onLeave: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-xl">
        <div className="p-6 text-center">
          <div className="mx-auto w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle className="h-6 w-6 text-yellow-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Unsaved Changes</h3>
          <p className="text-gray-600 mb-6">
            You have unsaved changes. Are you sure you want to leave? Your changes will be lost.
          </p>
          <div className="flex gap-3">
            <button
              onClick={onLeave}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700"
            >
              Leave
            </button>
            <button
              onClick={onStay}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Stay & Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== Success Toast ====================

function SuccessToast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="fixed top-4 right-4 z-50 animate-in fade-in slide-in-from-top-2">
      <div className="bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3">
        <Check className="h-5 w-5" />
        <span>{message}</span>
        <button onClick={onClose} className="p-1 hover:bg-green-700 rounded">
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

// ==================== Main Component ====================

export default function EditSellerListingPage() {
  const router = useRouter();
  const params = useParams();
  const listingId = params.id as string;
  const { user, getIdToken, loading: authLoading } = useAuth();
  
  // Data states
  const [listing, setListing] = useState<SellerListing | null>(null);
  const [specTemplate, setSpecTemplate] = useState<B2BSpecTemplate | null>(null);
  const [categorySettings, setCategorySettings] = useState<{ allowedSellerTypes?: string[] } | null>(null);
  
  // Loading states
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingImages, setUploadingImages] = useState(false);
  const [uploadingVideos, setUploadingVideos] = useState(false);
  const [uploadingDatasheet, setUploadingDatasheet] = useState(false);
  
  // UI states
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);
  
  // Form state
  const [form, setForm] = useState<FormState | null>(null);
  const initialFormRef = useRef<string | null>(null);

  // Token ref
  const [token, setToken] = useState<string | null>(null);

  // Load listing on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const authToken = await getIdToken();
        if (!authToken) {
          router.push('/login');
          return;
        }
        setToken(authToken);
        
        // Load listing - CRITICAL: specTemplate now comes from listing response
        const response = await getSellerListing(authToken, listingId);
        const { listing: lst, specTemplate: template } = response;
        setListing(lst);
        
        // Set spec template from listing response (variant-based, not category-based)
        if (template && template.fields && template.fields.length > 0) {
          setSpecTemplate(template);
          console.log('[SPEC_TEMPLATE] Loaded from listing response:', template);
        } else {
          console.log('[SPEC_TEMPLATE] No template in listing response, will try category fallback');
        }
        
        // Initialize form with listing data - STRICT camelCase
        const attrs: Record<string, AttributeFieldValue> = {};
        if (lst.attributes) {
          Object.entries(lst.attributes).forEach(([key, value]) => {
            attrs[key] = { value: value as string | number | boolean, touched: false };
          });
        }
        
        // Build pricingTiers from listing - STRICT camelCase model
        const pricingTiers: PricingTier[] = lst.pricingTiers && lst.pricingTiers.length > 0 
          ? lst.pricingTiers.map(t => ({
              minQty: t.minQty,
              maxQty: t.maxQty,
              pricePerUnit: t.pricePerUnit,
              currency: t.currency || 'INR'
            }))
          : [{ minQty: 1, maxQty: null, pricePerUnit: 0 }];
        
        const initialForm: FormState = {
          categoryId: lst.categoryId || '',
          categoryName: lst.categoryName || '',
          productId: lst.productId || '',
          productName: lst.productName || '',
          sellerType: lst.sellerRole || 'distributor',
          attributes: attrs,
          description: lst.description || '',
          moq: lst.moq || 1,
          stock: lst.stock || 0,
          maxCapacity: lst.maxCapacity || null,
          leadTime: lst.leadTime || null,
          pricingType: 'fixed',
          pricingTiers,
          images: lst.images || [],
          videos: lst.videos || [],  // Product demo videos
          datasheetUrl: lst.datasheetUrl || '',
          status: lst.status || 'draft'
        };
        
        setForm(initialForm);
        initialFormRef.current = JSON.stringify(initialForm);
        
        // Load spec template if NOT already from listing response
        // PRIORITY: variant.templateVersions > product.specTemplateIds > category.specTemplate
        if (!template && lst.categoryId) {
          try {
            const templateData = await getCategorySpecTemplate(authToken, lst.categoryId);
            if (templateData.specTemplate?.fields && templateData.specTemplate.fields.length > 0) {
              setSpecTemplate(templateData.specTemplate);
              console.log('[SPEC_TEMPLATE] Loaded from category fallback:', templateData.specTemplate);
              
              // Initialize missing attribute fields from category template
              const updatedAttrs = { ...attrs };
              templateData.specTemplate.fields.forEach((field: { key: string; fieldType?: string }) => {
                if (!(field.key in updatedAttrs)) {
                  updatedAttrs[field.key] = { value: field.fieldType === 'boolean' ? false : '', touched: false };
                }
              });
              setForm(prev => prev ? { ...prev, attributes: updatedAttrs } : prev);
            }
            setCategorySettings(templateData.category?.settings || null);
          } catch {
            console.log('[SPEC_TEMPLATE] No category template available');
          }
        } else if (template?.fields) {
          // Initialize attribute fields from listing's template
          const updatedAttrs = { ...attrs };
          template.fields.forEach((field: { key: string; fieldType?: string }) => {
            if (!(field.key in updatedAttrs)) {
              updatedAttrs[field.key] = { value: field.fieldType === 'boolean' ? false : '', touched: false };
            }
          });
          setForm(prev => prev ? { ...prev, attributes: updatedAttrs } : prev);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load listing');
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      if (!user) {
        router.push('/login');
      } else {
        loadData();
      }
    }
  }, [user, authLoading, getIdToken, router, listingId]);

  // Track unsaved changes
  useEffect(() => {
    if (form && initialFormRef.current) {
      const currentFormStr = JSON.stringify(form);
      setHasUnsavedChanges(currentFormStr !== initialFormRef.current);
    }
  }, [form]);

  // Browser beforeunload warning
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  // Handle navigation with unsaved changes
  const handleNavigation = (path: string) => {
    if (hasUnsavedChanges) {
      setPendingNavigation(path);
      setShowUnsavedModal(true);
    } else {
      router.push(path);
    }
  };

  // Handle attribute field change
  const handleAttributeChange = (key: string, value: string | number | boolean) => {
    setForm(prev => prev ? {
      ...prev,
      attributes: {
        ...prev.attributes,
        [key]: { value, touched: true }
      }
    } : prev);
  };

  // Handle image upload
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !token || !form) return;
    
    // Validate max count (5 images)
    if (form.images.length + files.length > 5) {
      setError('Maximum 5 images allowed');
      return;
    }
    
    // Validate individual file sizes (5MB each)
    const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5MB
    for (const file of Array.from(files)) {
      if (file.size > MAX_IMAGE_SIZE) {
        setError(`Image "${file.name}" exceeds 5MB limit`);
        return;
      }
      if (!file.type.startsWith('image/')) {
        setError(`File "${file.name}" is not a valid image`);
        return;
      }
    }
    
    setUploadingImages(true);
    setError(null);
    
    try {
      const result = await uploadProductImages(token, Array.from(files));
      setForm(prev => prev ? {
        ...prev,
        images: [...prev.images, ...result.images]
      } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload images');
    } finally {
      setUploadingImages(false);
    }
  };

  // Remove image
  const removeImage = (index: number) => {
    setForm(prev => prev ? {
      ...prev,
      images: prev.images.filter((_, i) => i !== index)
    } : prev);
  };

  // Validate video duration (max 30 seconds)
  const validateVideoDuration = (file: File): Promise<boolean> => {
    return new Promise((resolve, reject) => {
      const video = document.createElement('video');
      video.preload = 'metadata';
      
      video.onloadedmetadata = () => {
        URL.revokeObjectURL(video.src);
        if (video.duration > 30) {
          reject(new Error('Video must be under 30 seconds'));
        } else {
          resolve(true);
        }
      };
      
      video.onerror = () => {
        URL.revokeObjectURL(video.src);
        reject(new Error('Invalid video file'));
      };
      
      video.src = URL.createObjectURL(file);
    });
  };

  // Handle video upload
  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !token || !form) return;
    
    // Max 2 videos total
    if (form.videos.length + files.length > 2) {
      setError('Maximum 2 videos allowed');
      return;
    }
    
    setUploadingVideos(true);
    setError(null);
    
    try {
      // Validate each video
      for (const file of Array.from(files)) {
        // Check file type
        if (!file.type.startsWith('video/')) {
          throw new Error('Only video files are allowed');
        }
        
        // Check file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
          throw new Error('Each video must be under 5MB');
        }
        
        // Check duration (max 30 seconds)
        await validateVideoDuration(file);
      }
      
      // Upload videos
      const result = await uploadProductVideos(token, Array.from(files));
      setForm(prev => prev ? {
        ...prev,
        videos: [...prev.videos, ...result.videos]
      } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload videos');
    } finally {
      setUploadingVideos(false);
    }
  };

  // Remove video
  const removeVideo = (index: number) => {
    setForm(prev => prev ? {
      ...prev,
      videos: prev.videos.filter((_, i) => i !== index)
    } : prev);
  };

  // Handle datasheet upload
  const handleDatasheetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !token) return;
    
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are allowed for datasheets');
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      setError('Datasheet file must be less than 10MB');
      return;
    }
    
    setUploadingDatasheet(true);
    setError(null);
    
    try {
      const result = await uploadProductDatasheet(token, file);
      setForm(prev => prev ? {
        ...prev,
        datasheetUrl: result.url
      } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload datasheet');
    } finally {
      setUploadingDatasheet(false);
    }
  };

  // Remove datasheet
  const removeDatasheet = () => {
    setForm(prev => prev ? { ...prev, datasheetUrl: '' } : prev);
  };

  // Add pricing tier - STRICT camelCase
  const addPricingTier = () => {
    if (!form || form.pricingTiers.length >= 10) return;
    
    const lastTier = form.pricingTiers[form.pricingTiers.length - 1];
    const newMin = (lastTier.maxQty || lastTier.minQty) + 1;
    
    setForm(prev => prev ? {
      ...prev,
      pricingTiers: [
        ...prev.pricingTiers.slice(0, -1),
        { ...lastTier, maxQty: newMin - 1 },
        { minQty: newMin, maxQty: null, pricePerUnit: 0 }
      ]
    } : prev);
  };

  // Remove pricing tier
  const removePricingTier = (index: number) => {
    if (!form || form.pricingTiers.length <= 1) return;
    setForm(prev => prev ? {
      ...prev,
      pricingTiers: prev.pricingTiers.filter((_, i) => i !== index)
    } : prev);
  };

  // Update pricing tier - STRICT camelCase fields
  const updatePricingTier = (index: number, field: keyof PricingTier, value: number | null) => {
    setForm(prev => prev ? {
      ...prev,
      pricingTiers: prev.pricingTiers.map((tier, i) => 
        i === index ? { ...tier, [field]: value } : tier
      )
    } : prev);
  };

  // Validate form - STRICT validation rules
  const validateForm = (): string | null => {
    if (!form) return 'Form not loaded';
    
    // MOQ validation
    if (form.moq < 1) return 'MOQ must be at least 1';
    
    // Stock validation
    if (form.stock < 0) return 'Stock cannot be negative';
    
    // At least 1 image is mandatory
    if (form.images.length === 0) {
      return 'Please upload at least 1 product image';
    }
    
    // Max 5 images allowed
    if (form.images.length > 5) {
      return 'Maximum 5 images allowed';
    }
    
    // Check mandatory attribute fields
    if (specTemplate?.fields) {
      for (const field of specTemplate.fields) {
        const isMandatory = field.isMandatory === true || (field as { required?: boolean }).required === true;
        if (isMandatory) {
          const attr = form.attributes[field.key];
          if (!attr || attr.value === '' || attr.value === null || attr.value === undefined) {
            return `${field.label} is required`;
          }
        }
      }
    }
    
    // Validate pricing tiers - STRICT rules
    if (form.pricingType !== 'rfq_only') {
      // At least 1 tier required
      if (form.pricingTiers.length === 0) {
        return 'At least one pricing tier is required';
      }
      
      // minQty must be ascending
      let prevMax = 0;
      for (const tier of form.pricingTiers) {
        if (tier.minQty <= prevMax) {
          return 'Pricing tier quantities must be in ascending order';
        }
        if (tier.pricePerUnit <= 0) {
          return 'All price tiers must have a price greater than 0';
        }
        prevMax = tier.maxQty || tier.minQty;
      }
    }
    
    return null;
  };

  // Submit form - Save Changes (FINAL ARCHITECTURE - camelCase, attributes)
  const handleSubmit = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    
    if (!token || !form) return;
    
    setSubmitting(true);
    setError(null);
    
    try {
      // Extract raw attribute values (remove touched tracking)
      const attributesPayload: Record<string, string | number | boolean> = {};
      Object.entries(form.attributes).forEach(([key, val]) => {
        if (val.value !== '' && val.value !== null && val.value !== undefined) {
          attributesPayload[key] = val.value;
        }
      });
      
      // Update listing details - FINAL ARCHITECTURE payload (camelCase, includes attributes)
      await updateSellerListing(token, listingId, {
        description: form.description || undefined,
        images: form.images,
        videos: form.videos.length > 0 ? form.videos : undefined,  // Optional videos
        moq: form.moq,
        stock: form.stock,
        maxCapacity: form.maxCapacity || undefined,
        leadTime: form.leadTime || undefined,
        datasheetUrl: form.datasheetUrl || undefined,
        attributes: attributesPayload  // Send attributes - backend will create new variant if changed
      });
      
      // Update pricing tiers separately
      await updateSellerPricing(token, listingId, {
        pricingTiers: form.pricingTiers
      });
      
      // Update initial form ref to current state
      initialFormRef.current = JSON.stringify(form);
      setHasUnsavedChanges(false);
      
      setSuccessToast('Changes saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSubmitting(false);
    }
  };

  // Publish listing
  const handlePublish = async () => {
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    
    if (!token || !form) return;
    
    setSubmitting(true);
    setError(null);
    
    try {
      // Save first
      await handleSubmit();
      
      // Then publish
      await publishSellerListing(token, listingId);
      
      setSuccessToast('Listing published successfully!');
      
      // Redirect to listings after short delay
      setTimeout(() => {
        router.push('/seller/listings?published=true');
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish listing');
    } finally {
      setSubmitting(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!form || !listing) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Listing Not Found</h2>
          <p className="text-gray-500 mb-4">{error || 'Unable to load listing'}</p>
          <Link href="/seller/listings" className="text-blue-600 hover:underline">
            ← Back to Listings
          </Link>
        </div>
      </div>
    );
  }

  const statusColors: Record<string, { bg: string; text: string; label: string }> = {
    draft: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Draft' },
    active: { bg: 'bg-green-100', text: 'text-green-700', label: 'Published' },
    paused: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Paused' },
    archived: { bg: 'bg-red-100', text: 'text-red-700', label: 'Archived' }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Unsaved Changes Modal */}
      {showUnsavedModal && (
        <UnsavedChangesModal
          onStay={() => setShowUnsavedModal(false)}
          onLeave={() => {
            setShowUnsavedModal(false);
            if (pendingNavigation) {
              router.push(pendingNavigation);
            }
          }}
        />
      )}
      
      {/* Success Toast */}
      {successToast && (
        <SuccessToast message={successToast} onClose={() => setSuccessToast(null)} />
      )}

      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => handleNavigation('/seller/listings')}
              className="p-2 hover:bg-gray-100 rounded-lg"
              data-testid="back-btn"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold text-gray-900">Edit Listing</h1>
                <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[form.status]?.bg || 'bg-gray-100'} ${statusColors[form.status]?.text || 'text-gray-700'}`}>
                  {statusColors[form.status]?.label || form.status}
                </span>
                {hasUnsavedChanges && (
                  <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
                    Unsaved
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500">{form.productName}</p>
            </div>
          </div>
          
          {/* Progress Steps */}
          <div className="flex items-center gap-2 mt-4">
            {[
              { num: 1, label: 'Product' },
              { num: 2, label: 'Attributes' },
              { num: 3, label: 'Commercial' }
            ].map((step, idx) => (
              <div key={step.num} className="flex items-center">
                <button
                  onClick={() => setCurrentStep(step.num)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition ${
                    currentStep === step.num
                      ? 'bg-blue-600 text-white'
                      : currentStep > step.num
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                  data-testid={`step-${step.num}`}
                >
                  {currentStep > step.num ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <span className="w-5 h-5 flex items-center justify-center">{step.num}</span>
                  )}
                  {step.label}
                </button>
                {idx < 2 && <ChevronRight className="h-4 w-4 text-gray-400 mx-1" />}
              </div>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-700">
            <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-auto"><X className="h-4 w-4" /></button>
          </div>
        )}

        {/* Step 1: Product Info (READ-ONLY) */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Package className="h-5 w-5 text-blue-600" />
                Product Information
              </h2>
              
              <div className="p-4 bg-blue-50 rounded-lg mb-6">
                <div className="flex items-center gap-2 text-blue-800">
                  <Info className="h-5 w-5" />
                  <span className="font-medium">Product and Category cannot be changed after creation.</span>
                </div>
                <p className="text-sm text-blue-600 mt-1">
                  To list a different product, create a new listing.
                </p>
              </div>
              
              {/* Category (Disabled) */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Category
                </label>
                <input
                  type="text"
                  value={form.categoryName}
                  disabled
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                  data-testid="category-display"
                />
              </div>
              
              {/* Product Name (Disabled) */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Product
                </label>
                <input
                  type="text"
                  value={form.productName}
                  disabled
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                  data-testid="product-display"
                />
              </div>
              
              {/* Seller Type (Disabled for non-draft) */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Seller Type
                </label>
                {form.status === 'draft' ? (
                  <select
                    value={form.sellerType}
                    onChange={(e) => setForm(prev => prev ? { ...prev, sellerType: e.target.value } : prev)}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    data-testid="seller-type-select"
                  >
                    {(categorySettings?.allowedSellerTypes || ['manufacturer', 'distributor', 'dealer']).map(type => (
                      <option key={type} value={type}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    value={form.sellerType.charAt(0).toUpperCase() + form.sellerType.slice(1)}
                    disabled
                    className="w-full px-4 py-2.5 border border-gray-200 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                  />
                )}
              </div>
            </div>
            
            {/* Navigation */}
            <div className="flex justify-end">
              <button
                onClick={() => setCurrentStep(2)}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                data-testid="next-step-1"
              >
                Continue to Attributes
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Product Attributes */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Layers className="h-5 w-5 text-purple-600" />
                Product Attributes
              </h2>
              
              {specTemplate?.fields && specTemplate.fields.length > 0 ? (
                <div className="space-y-4">
                  {specTemplate.fields.map(field => {
                    const isMandatory = field.isMandatory === true || (field as { required?: boolean }).required === true;
                    const isLocked = field.isLockedAfterCreate && form.status !== 'draft';
                    
                    return (
                      <div key={field.key}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {field.label}
                          {isMandatory && <span className="text-red-500 ml-1">*</span>}
                          {field.unit && <span className="text-gray-400 font-normal ml-1">({field.unit})</span>}
                          {isLocked && <span className="text-orange-500 text-xs ml-2">(Locked)</span>}
                        </label>
                        
                        {field.fieldType === 'dropdown' && field.options ? (
                          <select
                            value={String(form.attributes[field.key]?.value || '')}
                            onChange={(e) => handleAttributeChange(field.key, e.target.value)}
                            disabled={isLocked}
                            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 bg-white ${isLocked ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                            data-testid={`attr-${field.key}`}
                            required={isMandatory}
                          >
                            <option value="">Select {field.label}</option>
                            {field.options.map(opt => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        ) : field.fieldType === 'boolean' ? (
                          <div className="flex gap-4">
                            <label className="flex items-center gap-2">
                              <input
                                type="radio"
                                checked={form.attributes[field.key]?.value === true}
                                onChange={() => handleAttributeChange(field.key, true)}
                                disabled={isLocked}
                                className="h-4 w-4 text-blue-600"
                              />
                              Yes
                            </label>
                            <label className="flex items-center gap-2">
                              <input
                                type="radio"
                                checked={form.attributes[field.key]?.value === false}
                                onChange={() => handleAttributeChange(field.key, false)}
                                disabled={isLocked}
                                className="h-4 w-4 text-blue-600"
                              />
                              No
                            </label>
                          </div>
                        ) : field.fieldType === 'number' ? (
                          <input
                            type="number"
                            value={form.attributes[field.key]?.value as number || ''}
                            onChange={(e) => handleAttributeChange(field.key, parseFloat(e.target.value) || 0)}
                            placeholder={field.placeholder || `Enter ${field.label}`}
                            min={field.minValue}
                            max={field.maxValue}
                            disabled={isLocked}
                            className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 ${isLocked ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                            data-testid={`attr-${field.key}`}
                          />
                        ) : (
                          <input
                            type="text"
                            value={String(form.attributes[field.key]?.value || '')}
                            onChange={(e) => handleAttributeChange(field.key, e.target.value)}
                            placeholder={field.placeholder || `Enter ${field.label}`}
                            disabled={isLocked}
                            className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 ${isLocked ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                            data-testid={`attr-${field.key}`}
                          />
                        )}
                        
                        {field.helpText && (
                          <p className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                            <HelpCircle className="h-3 w-3" />
                            {field.helpText}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="py-8 text-center text-gray-500">
                  <FileText className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                  <p>No specification template for this category.</p>
                  <p className="text-sm">You can add a description below.</p>
                </div>
              )}
              
              {/* Description */}
              <div className="mt-6 pt-6 border-t">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Additional Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm(prev => prev ? { ...prev, description: e.target.value } : prev)}
                  placeholder="Add any additional details about your product..."
                  rows={4}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  data-testid="description-input"
                />
              </div>
            </div>
            
            {/* Navigation */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(1)}
                className="px-6 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                onClick={() => setCurrentStep(3)}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                data-testid="next-step-2"
              >
                Continue to Commercial Terms
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Commercial Terms */}
        {currentStep === 3 && (
          <div className="space-y-6">
            {/* Images */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Upload className="h-5 w-5 text-green-600" />
                Product Images <span className="text-red-500">*</span>
              </h2>
              <p className="text-sm text-gray-500 mb-4">Upload at least 1 image (maximum 5). First image will be the main product image.</p>
              
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 mb-4">
                {form.images.map((img, idx) => (
                  <div key={idx} className="relative aspect-square rounded-lg overflow-hidden bg-gray-100 group">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={img} alt={`Product ${idx + 1}`} className="w-full h-full object-cover" />
                    {idx === 0 && (
                      <span className="absolute top-2 left-2 px-2 py-0.5 bg-blue-600 text-white text-xs rounded">Main</span>
                    )}
                    <button
                      type="button"
                      onClick={() => removeImage(idx)}
                      className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition"
                      data-testid={`remove-image-${idx}`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
                
                {form.images.length < 5 && (
                  <label className={`aspect-square rounded-lg border-2 border-dashed cursor-pointer flex flex-col items-center justify-center transition ${
                    form.images.length === 0 ? 'border-red-300 hover:border-red-500 bg-red-50' : 'border-gray-300 hover:border-blue-500'
                  }`}>
                    {uploadingImages ? (
                      <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                    ) : (
                      <>
                        <Plus className={`h-8 w-8 ${form.images.length === 0 ? 'text-red-400' : 'text-gray-400'}`} />
                        <span className={`text-xs mt-1 ${form.images.length === 0 ? 'text-red-500' : 'text-gray-500'}`}>
                          {form.images.length === 0 ? 'Required' : 'Add Image'}
                        </span>
                      </>
                    )}
                    <input
                      type="file"
                      accept="image/jpeg,image/jpg,image/png,image/webp,image/heic,image/heif"
                      multiple
                      onChange={handleImageUpload}
                      className="hidden"
                      data-testid="image-upload"
                    />
                  </label>
                )}
              </div>
              
              <p className={`text-sm ${form.images.length === 0 ? 'text-red-500' : 'text-gray-500'}`}>
                {form.images.length}/5 images uploaded {form.images.length === 0 && '(minimum 1 required)'}
              </p>
            </div>

            {/* Product Videos (Optional) */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
                <Video className="h-5 w-5 text-purple-600" />
                Product Demo Videos <span className="text-xs font-normal text-gray-500">(Optional)</span>
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Upload up to 2 videos showcasing your product (max 30 seconds, 5MB each). 
                <span className="text-purple-600 font-medium"> Videos can significantly boost buyer interest!</span>
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                {form.videos.map((videoUrl, idx) => (
                  <div key={idx} className="relative aspect-video rounded-lg overflow-hidden bg-gray-900 group">
                    <video 
                      src={videoUrl} 
                      className="w-full h-full object-contain"
                      controls
                      preload="metadata"
                    />
                    <button
                      type="button"
                      onClick={() => removeVideo(idx)}
                      className="absolute top-2 right-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition z-10"
                    >
                      <X className="h-4 w-4" />
                    </button>
                    {idx === 0 && (
                      <span className="absolute top-2 left-2 px-2 py-0.5 bg-purple-600 text-white text-xs rounded flex items-center gap-1">
                        <Play className="h-3 w-3" /> Main Video
                      </span>
                    )}
                  </div>
                ))}
                
                {form.videos.length < 2 && (
                  <label className="aspect-video rounded-lg border-2 border-dashed border-gray-300 hover:border-purple-500 cursor-pointer flex flex-col items-center justify-center transition bg-gray-50 hover:bg-purple-50">
                    {uploadingVideos ? (
                      <>
                        <Loader2 className="h-8 w-8 animate-spin text-purple-400" />
                        <span className="text-sm mt-2 text-purple-600">Uploading...</span>
                      </>
                    ) : (
                      <>
                        <Video className="h-10 w-10 text-gray-400" />
                        <span className="text-sm mt-2 text-gray-500">Add Video</span>
                        <span className="text-xs text-gray-400 mt-1">Max 30s, 5MB</span>
                      </>
                    )}
                    <input
                      type="file"
                      accept="video/mp4,video/webm,video/quicktime"
                      onChange={handleVideoUpload}
                      className="hidden"
                      data-testid="video-upload"
                    />
                  </label>
                )}
              </div>
              
              <p className="text-sm text-gray-500">
                {form.videos.length}/2 videos uploaded
              </p>
            </div>

            {/* Availability - STRICT camelCase fields */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Clock className="h-5 w-5 text-orange-600" />
                Availability & Lead Time
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Minimum Order Quantity (MOQ) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={form.moq}
                    onChange={(e) => setForm(prev => prev ? { ...prev, moq: parseInt(e.target.value) || 1 } : prev)}
                    min={1}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="moq-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock Available
                  </label>
                  <input
                    type="number"
                    value={form.stock}
                    onChange={(e) => setForm(prev => prev ? { ...prev, stock: parseInt(e.target.value) || 0 } : prev)}
                    min={0}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="stock-input"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Maximum Capacity (per order)
                  </label>
                  <input
                    type="number"
                    value={form.maxCapacity || ''}
                    onChange={(e) => setForm(prev => prev ? { ...prev, maxCapacity: parseInt(e.target.value) || null } : prev)}
                    min={1}
                    placeholder="Unlimited"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Lead Time (Days)
                  </label>
                  <input
                    type="number"
                    value={form.leadTime || ''}
                    onChange={(e) => setForm(prev => prev ? { ...prev, leadTime: parseInt(e.target.value) || null } : prev)}
                    min={0}
                    placeholder="e.g., 7"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    data-testid="leadtime-input"
                  />
                </div>
              </div>
            </div>

            {/* Pricing - STRICT camelCase with PricingTier model */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-emerald-600" />
                Pricing
              </h2>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pricing Type
                </label>
                <div className="flex gap-4 flex-wrap">
                  {[
                    { value: 'fixed', label: 'Fixed Price', desc: 'Show exact price' },
                    { value: 'negotiable', label: 'Negotiable', desc: 'Price shown, open to negotiation' },
                    { value: 'rfq_only', label: 'RFQ Only', desc: 'Price hidden, request quote' }
                  ].map(opt => (
                    <label 
                      key={opt.value} 
                      className={`flex-1 min-w-[140px] p-4 border rounded-lg cursor-pointer transition ${
                        form.pricingType === opt.value 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="pricingType"
                        value={opt.value}
                        checked={form.pricingType === opt.value}
                        onChange={(e) => setForm(prev => prev ? { ...prev, pricingType: e.target.value as FormState['pricingType'] } : prev)}
                        className="sr-only"
                      />
                      <div className="font-medium text-gray-900">{opt.label}</div>
                      <div className="text-xs text-gray-500 mt-1">{opt.desc}</div>
                    </label>
                  ))}
                </div>
              </div>
              
              {form.pricingType !== 'rfq_only' && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-sm font-medium text-gray-700">
                      Price Tiers
                    </label>
                    {form.pricingTiers.length < 10 && (
                      <button
                        type="button"
                        onClick={addPricingTier}
                        className="text-sm text-blue-600 hover:bg-blue-50 px-3 py-1 rounded-lg"
                      >
                        + Add Tier
                      </button>
                    )}
                  </div>
                  
                  <div className="space-y-3">
                    {form.pricingTiers.map((tier, idx) => (
                      <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-1 grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Min Qty</label>
                            <input
                              type="number"
                              value={tier.minQty}
                              onChange={(e) => updatePricingTier(idx, 'minQty', parseInt(e.target.value) || 1)}
                              min={1}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Max Qty</label>
                            <input
                              type="number"
                              value={tier.maxQty || ''}
                              onChange={(e) => updatePricingTier(idx, 'maxQty', parseInt(e.target.value) || null)}
                              placeholder="∞"
                              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Price/Unit (₹)</label>
                            <input
                              type="number"
                              value={tier.pricePerUnit || ''}
                              onChange={(e) => updatePricingTier(idx, 'pricePerUnit', Math.round(parseFloat(e.target.value) * 100) / 100 || 0)}
                              min={0}
                              step={1}
                              className="w-full px-3 py-1.5 border border-gray-300 rounded text-sm"
                              data-testid={`price-tier-${idx}`}
                            />
                          </div>
                        </div>
                        {form.pricingTiers.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removePricingTier(idx)}
                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Datasheet */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileText className="h-5 w-5 text-gray-600" />
                Datasheet (Optional)
              </h2>
              
              {form.datasheetUrl ? (
                <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
                  <FileText className="h-8 w-8 text-blue-600" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">Datasheet uploaded</p>
                    <a 
                      href={form.datasheetUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline"
                    >
                      View file
                    </a>
                  </div>
                  <button
                    type="button"
                    onClick={removeDatasheet}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 transition">
                  {uploadingDatasheet ? (
                    <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-400 mb-2" />
                      <p className="text-sm text-gray-500">Click to upload datasheet (PDF)</p>
                      <p className="text-xs text-gray-400 mt-1">Max 10MB</p>
                    </>
                  )}
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={handleDatasheetUpload}
                    className="hidden"
                    data-testid="datasheet-upload"
                  />
                </label>
              )}
            </div>
            
            {/* Navigation & Actions */}
            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep(2)}
                className="px-6 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <div className="flex gap-3">
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !hasUnsavedChanges}
                  className="px-6 py-2.5 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:opacity-50 flex items-center gap-2"
                  data-testid="save-changes"
                >
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save Changes
                </button>
                {(form.status === 'draft' || form.status === 'paused') && (
                  <button
                    onClick={handlePublish}
                    disabled={submitting}
                    className="px-8 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                    data-testid="publish-listing"
                  >
                    {submitting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Check className="h-4 w-4" />
                    )}
                    {form.status === 'paused' ? 'Republish' : 'Publish'}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
